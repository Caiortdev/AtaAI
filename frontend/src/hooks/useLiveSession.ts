import { useCallback, useEffect, useRef, useState } from "react";

import { createLiveWebSocket } from "../api";
import { useWorkspaceStore } from "../store";
import type { LiveMessage, LiveSessionState } from "../types";

const AUDIO_TIMESLICE_MS = 1000;

type UseLiveSessionReturn = {
  state: LiveSessionState;
  transcript: string[];
  draft: string;
  error: string | null;
  elapsedSeconds: number;
  start: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => void;
};

export function useLiveSession(meetingId: string | null): UseLiveSessionReturn {
  const [state, setState] = useState<LiveSessionState>("idle");
  const [transcript, setTranscript] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const setIsRecording = useWorkspaceStore((s) => s.setIsRecording);

  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const stateRef = useRef<LiveSessionState>("idle");

  stateRef.current = state;

  // Sync global recording indicator
  useEffect(() => {
    setIsRecording(state === "recording" || state === "paused");
  }, [state, setIsRecording]);

  const cleanup = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    recorderRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const start = useCallback(async () => {
    if (!meetingId) {
      setError("Selecione uma reuniao antes de gravar.");
      return;
    }

    setError(null);
    setTranscript([]);
    setDraft("");
    setElapsedSeconds(0);

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Permissao de microfone negada ou indisponivel.");
      return;
    }
    streamRef.current = stream;

    const ws = createLiveWebSocket(meetingId);
    wsRef.current = ws;

    ws.onopen = () => {
      setState("recording");
      startTimeRef.current = Date.now();
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          event.data.arrayBuffer().then((buffer) => {
            const base64 = arrayBufferToBase64(buffer);
            ws.send(JSON.stringify({ type: "audio", data: base64 }));
          });
        }
      };

      recorder.start(AUDIO_TIMESLICE_MS);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as LiveMessage;
        switch (message.type) {
          case "transcript":
            setTranscript((prev) => [...prev, message.text]);
            break;
          case "draft":
            setDraft(message.markdown);
            break;
          case "status":
            setState(message.state);
            if (message.state === "done") {
              cleanup();
            }
            break;
          case "error":
            setError(message.message);
            break;
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      setError("Conexao com o servidor perdida.");
      cleanup();
      setState("idle");
    };

    ws.onclose = (event) => {
      if (stateRef.current !== "done" && stateRef.current !== "idle") {
        if (event.reason) {
          setError(event.reason);
        }
        cleanup();
        setState("idle");
      }
    };
  }, [meetingId, cleanup]);

  const pause = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.pause();
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "pause" }));
    }
    setState("paused");
  }, []);

  const resume = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === "paused") {
      recorderRef.current.resume();
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "resume" }));
    }
    setState("recording");
  }, []);

  const stop = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop" }));
    }
    setState("finalizing");
  }, []);

  return { state, transcript, draft, error, elapsedSeconds, start, pause, resume, stop };
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
