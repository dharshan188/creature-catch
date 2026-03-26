import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export type DetectionStatus = "none" | "human" | "elephant" | "bear" | "giraffe";

const statusConfig: Record<DetectionStatus, { label: string; glowClass: string; colorClass: string; dot: string }> = {
  none:     { label: "Nothing Detected",  glowClass: "glow-safe",     colorClass: "bg-status-safe/20 text-status-safe border-status-safe/30",   dot: "bg-status-safe" },
  human:    { label: "Human Detected",    glowClass: "glow-human",    colorClass: "bg-status-human/20 text-status-human border-status-human/30", dot: "bg-status-human" },
  elephant: { label: "Elephant Detected", glowClass: "glow-elephant", colorClass: "bg-status-elephant/20 text-status-elephant border-status-elephant/30", dot: "bg-status-elephant" },
  bear:     { label: "Bear Detected",     glowClass: "glow-bear",     colorClass: "bg-status-bear/20 text-status-bear border-status-bear/30",   dot: "bg-status-bear" },
  giraffe:  { label: "Giraffe Detected",  glowClass: "glow-giraffe",  colorClass: "bg-status-giraffe/20 text-status-giraffe border-status-giraffe/30", dot: "bg-status-giraffe" },
};

interface Props {
  status: DetectionStatus;
}

export function StatusBadge({ status }: Props) {
  const config = statusConfig[status];
  const isAlert = status !== "none";

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={status}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={cn(
          "inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full border text-sm font-semibold",
          config.colorClass,
          config.glowClass,
          isAlert && "animate-pulse-glow"
        )}
      >
        <span className={cn("w-2.5 h-2.5 rounded-full", config.dot, isAlert && "animate-ping")} />
        <span className={cn("w-2.5 h-2.5 rounded-full absolute", config.dot)} />
        <span>{config.label}</span>
      </motion.div>
    </AnimatePresence>
  );
}
