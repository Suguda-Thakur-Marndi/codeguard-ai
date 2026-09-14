import React from "react";

interface DiffViewerProps {
  diffText: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diffText }) => {
  if (!diffText || diffText.trim() === "") {
    return (
      <div className="bg-slate-950 border border-slate-800 rounded-lg p-8 text-center text-slate-500 font-mono text-xs">
        No unified diff content recorded for this review job.
      </div>
    );
  }

  const lines = diffText.split("\n");

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden font-mono text-xs shadow-inner">
      <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-slate-400">
        <span className="font-semibold text-slate-300">Raw Unified Diff</span>
        <span className="text-[11px]">{lines.length} lines</span>
      </div>
      <div className="overflow-x-auto max-h-[550px] p-2 select-text">
        {lines.map((line, idx) => {
          let lineBg = "hover:bg-slate-900/50 text-slate-300";
          let lineSign = " ";

          if (line.startsWith("+++") || line.startsWith("---")) {
            lineBg = "bg-slate-900 text-slate-400 font-semibold";
          } else if (line.startsWith("@@")) {
            lineBg = "bg-cyan-950/30 text-cyan-400 font-medium py-0.5";
          } else if (line.startsWith("+")) {
            lineBg = "bg-emerald-950/40 text-emerald-300";
            lineSign = "+";
          } else if (line.startsWith("-")) {
            lineBg = "bg-rose-950/40 text-rose-300";
            lineSign = "-";
          } else if (line.startsWith("diff --git")) {
            lineBg = "bg-slate-800/80 text-blue-300 font-semibold mt-2 first:mt-0 py-1 border-t border-slate-700/50 first:border-0";
          }

          return (
            <div key={idx} className={`flex items-start px-2 py-0.5 rounded leading-relaxed ${lineBg}`}>
              <span className="w-10 select-none text-right pr-3 text-slate-600 font-mono text-[11px]">
                {idx + 1}
              </span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono">{line}</pre>
            </div>
          );
        })}
      </div>
    </div>
  );
};
