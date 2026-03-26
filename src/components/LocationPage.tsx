import { motion } from "framer-motion";
import { MapPin, Bell } from "lucide-react";

export function LocationPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-2xl font-bold text-foreground">Setup Location</h2>
        <p className="text-sm text-muted-foreground mt-1">Configure geofencing and location-based alerts</p>
      </div>

      <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center text-center min-h-[400px]">
        <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
          <MapPin className="text-accent" size={28} />
        </div>
        <h3 className="text-lg font-semibold text-foreground">Location-Based Alerts Coming Soon</h3>
        <p className="text-sm text-muted-foreground mt-2 max-w-sm">
          Set up geofencing zones and receive location-specific intrusion alerts for your farm perimeter.
        </p>
        <div className="flex items-center gap-2 mt-6 text-xs text-muted-foreground glass rounded-lg px-4 py-2">
          <Bell size={14} />
          <span>Alert system in development</span>
        </div>
      </div>
    </motion.div>
  );
}
