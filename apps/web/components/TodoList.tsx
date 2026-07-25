"use client";

import { useSwarmStore, type TodoItem } from "@/lib/store";

const STATUS_ICON: Record<TodoItem["status"], string> = {
  pending: "○",
  running: "◐",
  done:    "●",
  failed:  "✕",
};

const STATUS_COLOR: Record<TodoItem["status"], string> = {
  pending: "text-gh-dim",
  running: "text-gh-blue",
  done:    "text-gh-green",
  failed:  "text-gh-red",
};

const TEXT_COLOR: Record<TodoItem["status"], string> = {
  pending: "text-gh-dim",
  running: "text-gh-text",
  done:    "text-gh-dim/50 line-through decoration-gh-dim/30",
  failed:  "text-gh-red/70",
};

const ROLE_COLOR: Record<string, string> = {
  pm:       "text-role-pm",
  designer: "text-role-designer",
  frontend: "text-role-frontend",
  backend:  "text-role-backend",
  tester:   "text-role-tester",
  ops:      "text-role-ops",
};

function TodoRow({ todo }: { todo: TodoItem }) {
  const roleColor = ROLE_COLOR[todo.role] ?? "text-gh-dim";
  return (
    <div className="flex items-start gap-2 px-4 py-1.5 hover:bg-gh-muted/30 transition-colors">
      <span className={`mt-px shrink-0 font-mono text-[10px] ${STATUS_COLOR[todo.status]}`}>
        {STATUS_ICON[todo.status]}
      </span>
      <div className="min-w-0 flex-1">
        <p className={`text-[12px] leading-snug ${TEXT_COLOR[todo.status]}`}>
          {todo.description}
        </p>
        {todo.role && (
          <span className={`font-mono text-[9px] ${roleColor}`}>
            {todo.role}
          </span>
        )}
      </div>
    </div>
  );
}

export function TodoList() {
  const todos = useSwarmStore((s) => s.todos);
  if (todos.length === 0) return null;

  const done = todos.filter((t) => t.status === "done").length;
  const pct  = todos.length ? (done / todos.length) * 100 : 0;

  return (
    <div>
      <div className="px-4 pb-2 pt-1">
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-mono text-[10px] text-gh-dim tabular-nums">
            {done}/{todos.length}
          </span>
          <span className="font-mono text-[10px] text-gh-dim tabular-nums">
            {Math.round(pct)}%
          </span>
        </div>
        <div className="h-[3px] rounded-full bg-gh-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-gh-green transition-all duration-700 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <div>
        {todos.map((t) => <TodoRow key={t.id} todo={t} />)}
      </div>
    </div>
  );
}
