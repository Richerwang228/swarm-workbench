"use client";

import { useSwarmStore } from "@/lib/store";

export function TerminalPanel() {
  const lastToolCall = useSwarmStore((s) => s.lastToolCall);

  if (!lastToolCall) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 opacity-25 select-none">
        <span className="font-mono text-2xl text-gh-dim">$_</span>
        <p className="text-[11px] text-gh-dim">等待工具调用</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-4 font-mono text-[11px]">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-gh-green">$</span>
        <span className="text-gh-text font-semibold">{lastToolCall.tool}</span>
      </div>

      <div className="border-l-2 border-gh-border pl-3 mb-3">
        <p className="text-[9px] text-gh-dim uppercase tracking-widest mb-1">args</p>
        <pre className="whitespace-pre-wrap text-gh-text/70 text-[10px] leading-relaxed">
          {JSON.stringify(lastToolCall.args, null, 2)}
        </pre>
      </div>

      {lastToolCall.result && (
        <div className="border-l-2 border-gh-green/30 pl-3">
          <p className="text-[9px] text-gh-dim uppercase tracking-widest mb-1">result</p>
          <pre className="whitespace-pre-wrap text-gh-green/80 text-[10px] leading-relaxed">
            {lastToolCall.result.slice(0, 2000)}
          </pre>
        </div>
      )}
    </div>
  );
}
