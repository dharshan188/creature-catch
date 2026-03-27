import { useEffect, useMemo, useState } from "react";
import { StatusBadge, type DetectionStatus } from "./StatusBadge";
import { motion } from "framer-motion";
import { Wifi, Clock } from "lucide-react";

const STATUS_ENDPOINT = "http://127.0.0.1:5000/status";
const FEED_ENDPOINT = "http://127.0.0.1:5000/video_feed";

function mapLabelToStatus(label: string): DetectionStatus {
  if (label.includes("Human")) return "human";
  if (label.includes("Elephant")) return "elephant";
  if (label.includes("Bear")) return "bear";
  if (label.includes("Giraffe")) return "giraffe";
  return "none";
}

function statusDot(label: string): string {
  if (label.includes("Human")) return "🔴";
  if (label.includes("Elephant")) return "🟠";
  if (label.includes("Bear")) return "🟣";
  if (label.includes("Giraffe")) return "🟡";
  return "🟢";
}

export function LiveFeedPage() {
  const [status, setStatus] = useState<DetectionStatus>("none");
  const [statusLabel, setStatusLabel] = useState("Nothing Detected");
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await fetch(STATUS_ENDPOINT);
        if (!response.ok) {
          return;
        }

        const data = (await response.json()) as { status?: string };
        const backendStatus = data.status ?? "Nothing Detected";
        setStatusLabel(backendStatus);
        setStatus(mapLabelToStatus(backendStatus));
      } catch {
        setStatusLabel("Nothing Detected");
        setStatus("none");
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 500);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const statusClassName = useMemo(() => {
    if (status === "human") return "text-status-human";
    if (status === "elephant") return "text-status-elephant";
    if (status === "bear") return "text-status-bear";
    if (status === "giraffe") return "text-status-giraffe";
    return "text-status-safe";
  }, [status]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Live Monitoring</h2>
          <p className="text-sm text-muted-foreground mt-1">Real-time intrusion detection</p>
        </div>
        <StatusBadge status={status} />
      </div>

      <div
        id="status"
        className={`glass rounded-xl px-4 py-2 text-sm font-semibold transition-colors duration-300 ${statusClassName}`}
      >
        {statusDot(statusLabel)} {statusLabel}
      </div>

      <div className="glass rounded-2xl p-1.5 group max-w-4xl mx-auto">
        <div className="relative rounded-xl overflow-hidden aspect-video bg-secondary/50">
          <img
            id="videoFeed"
            src={FEED_ENDPOINT}
            alt="Live wildlife monitoring stream"
            className="w-full h-full object-cover"
          />

          <div className="absolute top-3 left-3 flex items-center gap-2">
            <span className="glass rounded-lg px-3 py-1 text-xs font-medium text-foreground flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-status-safe animate-pulse" />
              LIVE
            </span>
          </div>

          <div className="absolute top-3 right-3 flex items-center gap-2">
            <span className="glass rounded-lg px-3 py-1 text-xs text-muted-foreground flex items-center gap-1.5">
              <Wifi size={12} />
              CAM-01
            </span>
          </div>

          <div className="absolute bottom-3 right-3">
            <span className="glass rounded-lg px-3 py-1 text-xs text-muted-foreground flex items-center gap-1.5">
              <Clock size={12} />
              {time.toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
