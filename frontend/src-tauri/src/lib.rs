use serde::Deserialize;
use std::{
    fs::OpenOptions,
    io::{Read, Write},
    net::{TcpStream, ToSocketAddrs},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    thread,
    time::Duration,
};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const API_ADDR: &str = "127.0.0.1:8000";
const TAURI_ORIGIN: &str = "http://tauri.localhost";

#[derive(Deserialize)]
struct PdfPayload {
    filename: String,
    bytes: Vec<u8>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![save_pdf_to_downloads])
        .setup(|_app| {
            if !api_is_desktop_ready() {
                start_local_backend();
                wait_for_desktop_ready();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("erro ao iniciar AtaAI desktop");
}

#[tauri::command]
fn save_pdf_to_downloads(payload: PdfPayload) -> Result<String, String> {
    let downloads_dir = windows_downloads_dir().ok_or_else(|| {
        "Nao foi possivel localizar a pasta Downloads do Windows.".to_string()
    })?;
    std::fs::create_dir_all(&downloads_dir).map_err(|error| error.to_string())?;
    let path = unique_path(downloads_dir.join(sanitize_filename(&payload.filename)));
    std::fs::write(&path, payload.bytes).map_err(|error| error.to_string())?;
    Ok(path.to_string_lossy().into_owned())
}

fn api_is_desktop_ready() -> bool {
    api_has_auth_routes() && api_allows_tauri_origin()
}

fn api_has_auth_routes() -> bool {
    http_request("GET /openapi.json HTTP/1.1\r\nHost: 127.0.0.1:8000\r\nConnection: close\r\n\r\n")
        .is_some_and(|response| response.contains("/api/auth/register"))
}

fn api_allows_tauri_origin() -> bool {
    let request = format!(
        "OPTIONS /api/auth/login HTTP/1.1\r\n\
         Host: 127.0.0.1:8000\r\n\
         Origin: {TAURI_ORIGIN}\r\n\
         Access-Control-Request-Method: POST\r\n\
         Connection: close\r\n\r\n"
    );
    http_request(&request).is_some_and(|response| {
        let response = response.to_ascii_lowercase();
        response.contains(" 200 ok")
            && response.contains(&format!("access-control-allow-origin: {}", TAURI_ORIGIN))
    })
}

fn http_request(request: &str) -> Option<String> {
    let mut addrs = API_ADDR.to_socket_addrs().ok()?;
    let addr = addrs.next()?;
    let mut stream = TcpStream::connect_timeout(&addr, Duration::from_millis(350)).ok()?;

    let _ = stream.set_read_timeout(Some(Duration::from_millis(900)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(350)));

    stream.write_all(request.as_bytes()).ok()?;

    let mut response = String::new();
    stream.read_to_string(&mut response).ok()?;
    Some(response)
}

fn wait_for_desktop_ready() {
    for _ in 0..30 {
        if api_is_desktop_ready() {
            return;
        }
        thread::sleep(Duration::from_millis(250));
    }
}

fn start_local_backend() {
    let Some(backend_dir) = find_backend_dir() else {
        return;
    };
    let python = backend_dir.join(".venv").join("Scripts").join("python.exe");
    if !python.exists() {
        return;
    }
    let log_path = backend_dir.join("storage").join("desktop-backend.log");
    let _ = std::fs::create_dir_all(backend_dir.join("storage"));
    let stdout = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .ok();
    let stderr = stdout.as_ref().and_then(|file| file.try_clone().ok());

    let mut command = Command::new(python);
    command
        .args([
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ])
        .current_dir(backend_dir)
        .stdin(Stdio::null())
        .stdout(stdout.map(Stdio::from).unwrap_or_else(Stdio::null))
        .stderr(stderr.map(Stdio::from).unwrap_or_else(Stdio::null));

    #[cfg(windows)]
    command.creation_flags(0x08000000);

    let _ = command.spawn();
}

fn find_backend_dir() -> Option<PathBuf> {
    candidate_roots()
        .into_iter()
        .find_map(|root| backend_dir_from_root(&root))
}

fn candidate_roots() -> Vec<PathBuf> {
    let mut roots = Vec::new();

    if let Ok(exe_path) = std::env::current_exe() {
        roots.extend(exe_path.ancestors().map(Path::to_path_buf));
    }

    if let Ok(current_dir) = std::env::current_dir() {
        roots.extend(current_dir.ancestors().map(Path::to_path_buf));
    }

    roots
}

fn backend_dir_from_root(root: &Path) -> Option<PathBuf> {
    let direct = root.join("backend");
    if direct.join("app").join("main.py").exists() {
        return Some(direct);
    }

    let parent = root.parent()?.join("backend");
    if parent.join("app").join("main.py").exists() {
        return Some(parent);
    }

    None
}

fn sanitize_filename(filename: &str) -> String {
    let sanitized: String = filename
        .chars()
        .map(|character| match character {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '-',
            _ if character.is_control() => '-',
            _ => character,
        })
        .collect();
    let trimmed = sanitized.trim().trim_matches('.').trim();
    if trimmed.is_empty() {
        "ata-reuniao.pdf".to_string()
    } else if trimmed.to_ascii_lowercase().ends_with(".pdf") {
        trimmed.to_string()
    } else {
        format!("{trimmed}.pdf")
    }
}

fn windows_downloads_dir() -> Option<PathBuf> {
    std::env::var_os("USERPROFILE").map(|home| PathBuf::from(home).join("Downloads"))
}

fn unique_path(path: PathBuf) -> PathBuf {
    if !path.exists() {
        return path;
    }

    let parent = path.parent().map(Path::to_path_buf).unwrap_or_default();
    let stem = path
        .file_stem()
        .and_then(|value| value.to_str())
        .unwrap_or("ata-reuniao");
    let extension = path.extension().and_then(|value| value.to_str()).unwrap_or("pdf");

    for index in 1..1000 {
        let candidate = parent.join(format!("{stem}-{index}.{extension}"));
        if !candidate.exists() {
            return candidate;
        }
    }
    path
}
