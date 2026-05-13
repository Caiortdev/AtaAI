import { type ReactNode, useState } from "react";

type Tab = {
  id: string;
  label: string;
  content: ReactNode;
};

type TabsProps = {
  tabs: Tab[];
  defaultTab?: string;
  className?: string;
};

export function Tabs({ tabs, defaultTab, className = "" }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id || "");

  const activeContent = tabs.find((tab) => tab.id === activeTab)?.content;

  return (
    <div className={className}>
      <div className="flex gap-1 rounded-glass-sm bg-white/30 p-1 backdrop-blur-sm dark:bg-white/5">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`relative rounded-glass-xs px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.id
                ? "glass text-text-primary shadow-glass-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="mt-4 max-h-[calc(100vh-14rem)] overflow-y-auto">{activeContent}</div>
    </div>
  );
}
