import { useState, useEffect } from "react";
import { StatusBadge, type DetectionStatus } from "./StatusBadge";
import { motion } from "framer-motion";
import { Camera, Wifi, Clock } from "lucide-react";

const STATUSES: DetectionStatus[] = ["none", "human", "elephant", "bear", "giraffe"];

export function LiveFeedPage() {
  const [status, setStatus] = useState<DetectionStatus>("none");
  const [time, setTime] = useState(new Date());

  // Simulate status changes for demo
  useEffect(() => {
    const interval = setInterval(() => {
      setStatus(STATUSES[Math.floor(Math.random() * STATUSES.length)]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Live Monitoring</h2>
          <p className="text-sm text-muted-foreground mt-1">Real-time AI-powered intrusion detection</p>
        </div>
        <StatusBadge status={status} />
      </div>

      {/* Main feed card */}
      <div className="glass rounded-2xl p-1.5 group">
        <div className="relative rounded-xl overflow-hidden aspect-video bg-secondary/50">
          {/* Placeholder for /video_feed */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
            <Camera size={48} className="mb-3 opacity-40" />
            <p className="text-sm font-medium">Camera Feed</p>
            <p className="text-xs opacity-60 mt-1">Connect to /video_feed endpoint</p>
          </div>

          {/* Overlay info */}
          <div className="absolute top-3 left-3 flex items-center gap-2">
            <span className="glass rounded-lg px-3 py-1 text-xs font-medium text-foreground flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-status-human animate-pulse" />
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

          {/* Hover zoom */}
          <div className="absolute inset-0 transition-transform duration-500 group-hover:scale-[1.02]" />
        </div>
      </div>

      {/* Info cards row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Detection Model", value: "YOLOv8-Custom", sub: "5 classes" },
          { label: "Frame Rate", value: "30 FPS", sub: "1080p" },
          { label: "Uptime", value: "99.7%", sub: "Last 24h" },
        ].map((item) => (
          <div key={item.label} className="glass rounded-xl p-4">
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-lg font-semibold text-foreground mt-1">{item.value}</p>
            <p className="text-xs text-primary mt-0.5">{item.sub}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
