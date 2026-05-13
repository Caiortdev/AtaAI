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
      <div className="flex border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`relative px-4 py-2.5 text-sm font-medium transition ${
              activeTab === tab.id
                ? "text-accent"
                : "text-text-secondary hover:text-text-primary"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-accent" />
            )}
          </button>
        ))}
      </div>
      <div className="mt-4 max-h-[calc(100vh-14rem)] overflow-y-auto">{activeContent}</div>
    </div>
  );
}
