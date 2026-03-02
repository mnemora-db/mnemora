import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Episode } from "@/lib/mock-data";

interface EpisodeTimelineProps {
  episodes: Episode[];
}

const typeConfig: Record<
  Episode["type"],
  { label: string; color: string; dot: string }
> = {
  conversation: {
    label: "conversation",
    color: "border-blue-500/30 text-blue-400 bg-blue-500/5",
    dot: "bg-blue-500",
  },
  action: {
    label: "action",
    color: "border-purple-500/30 text-purple-400 bg-purple-500/5",
    dot: "bg-purple-500",
  },
  observation: {
    label: "observation",
    color: "border-green-500/30 text-green-400 bg-green-500/5",
    dot: "bg-green-500",
  },
  tool_call: {
    label: "tool_call",
    color: "border-amber-500/30 text-amber-400 bg-amber-500/5",
    dot: "bg-amber-500",
  },
};

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function EpisodeTimeline({ episodes }: EpisodeTimelineProps) {
  if (episodes.length === 0) {
    return (
      <p className="text-sm text-[#71717A] py-8 text-center">
        No episodes recorded.
      </p>
    );
  }

  // Group by session
  const sessions: Record<string, Episode[]> = {};
  for (const ep of episodes) {
    if (!sessions[ep.sessionId]) {
      sessions[ep.sessionId] = [];
    }
    sessions[ep.sessionId].push(ep);
  }

  return (
    <div className="space-y-8" role="feed" aria-label="Episode timeline">
      {Object.entries(sessions).map(([sessionId, sessionEpisodes]) => (
        <div key={sessionId}>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-mono text-[#71717A]">
              session: {sessionId}
            </span>
            <div className="flex-1 h-px bg-[#27272A]" aria-hidden="true" />
          </div>
          <ol className="relative border-l border-[#27272A] space-y-0 ml-2">
            {sessionEpisodes.map((episode, index) => {
              const config = typeConfig[episode.type];
              return (
                <li
                  key={episode.id}
                  className="relative pl-6 pb-6 last:pb-0"
                  aria-label={`${config.label} at ${formatTime(episode.timestamp)}`}
                >
                  {/* Timeline dot */}
                  <span
                    className={cn(
                      "absolute left-0 top-1 w-2.5 h-2.5 rounded-full border-2 border-[#111114] -translate-x-1/2",
                      config.dot
                    )}
                    aria-hidden="true"
                  />

                  <div className="flex items-start gap-3">
                    {/* Timestamp */}
                    <div className="shrink-0 text-right min-w-[90px]">
                      <p className="text-xs font-mono text-[#71717A]">
                        {formatTime(episode.timestamp)}
                      </p>
                      {index === sessionEpisodes.length - 1 && (
                        <p className="text-xs text-[#52525B]">
                          {formatDate(episode.timestamp)}
                        </p>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Badge
                          variant="outline"
                          className={`text-xs ${config.color}`}
                        >
                          {config.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-[#A1A1AA] leading-relaxed">
                        {episode.content}
                      </p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      ))}
    </div>
  );
}
