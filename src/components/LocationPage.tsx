import { motion } from "framer-motion";
import { MapPin, RefreshCcw, ExternalLink, Clock, AlertCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

type AlertItem = {
  title: string;
  link: string;
  city: string;
  time: string;
};

type NewsResponse = {
  city?: string;
  alerts?: AlertItem[];
  lastUpdated?: string;
};

const NEWS_ENDPOINT = "http://127.0.0.1:5000/news";
const NEWS_CITY_ENDPOINT = "http://127.0.0.1:5000/news/city";

export function LocationPage() {
  const [city, setCity] = useState("Nelambur");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchAlerts = useCallback(async (targetCity: string) => {
    const trimmedCity = targetCity.trim();
    if (!trimmedCity) return;

    setLoading(true);
    const loadingGuard = window.setTimeout(() => {
      setLoading(false);
    }, 8000);

    try {
      const url = `${NEWS_ENDPOINT}?city=${encodeURIComponent(trimmedCity)}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to fetch alerts");
      }
      const data = (await response.json()) as NewsResponse;
      console.log("ALERTS RESPONSE:", data);

      setAlerts(data.alerts || []);
      if (data.lastUpdated) {
        setLastUpdated(data.lastUpdated);
      }
    } catch (error) {
      console.error("Alert fetch error:", error);
      setAlerts([]);
    } finally {
      window.clearTimeout(loadingGuard);
      setLoading(false);
    }
  }, []);

  const saveCity = useCallback(async (targetCity: string) => {
    const trimmedCity = targetCity.trim();
    if (!trimmedCity) return;

    try {
      await fetch(NEWS_CITY_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city: trimmedCity }),
      });
    } catch (error) {
      console.error("Save city error:", error);
    }
  }, []);

  useEffect(() => {
    fetchAlerts(city);
    const interval = setInterval(() => fetchAlerts(city), 30000);
    return () => clearInterval(interval);
  }, [city, fetchAlerts]);

  const handleRefresh = async () => {
    await saveCity(city);
    await fetchAlerts(city);
  };

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleTimeString();
    } catch {
      return isoString;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-2xl font-bold text-foreground">Intrusion Alerts</h2>
        <p className="text-sm text-muted-foreground mt-1">Real-time wildlife intrusion and theft alerts from RSS feeds</p>
      </div>

      <div className="glass rounded-2xl p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin size={16} />
            <span>Select city to monitor for intrusion alerts</span>
          </div>
          {lastUpdated && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock size={12} />
              <span>Updated {formatTime(lastUpdated)}</span>
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            value={city}
            onChange={(event) => setCity(event.target.value)}
            placeholder="Enter city (e.g., Coimbatore)"
            className="flex-1 h-10 px-3 rounded-md bg-background border border-input text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading}
            className="h-10 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium inline-flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <RefreshCcw size={14} className={loading ? "animate-spin" : ""} />
            {loading ? "Checking..." : "Check Alerts"}
          </button>
        </div>

        <div className="alerts-container">
          {alerts && alerts.length > 0 ? (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground italic px-1">
                Showing latest {alerts.length} {alerts.length === 1 ? 'alert' : 'alerts'}
              </div>
              {alerts.map((item, index) => (
                <motion.div
                  key={`${item.link}-${index}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="alert-card"
                >
                  <div className="flex gap-3">
                    <AlertCircle size={20} className="text-destructive flex-shrink-0 mt-1" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-foreground">{item.title}</h4>
                      <div className="text-xs text-muted-foreground mt-2 space-y-1">
                        <div>📍 {item.city}</div>
                        <div>🕐 {item.time}</div>
                      </div>
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 mt-3 text-sm text-primary hover:underline"
                      >
                        <ExternalLink size={14} />
                        Read Source
                      </a>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="glass rounded-xl p-6 text-center">
              <p className="text-sm text-muted-foreground">No intrusion alerts found</p>
              <p className="text-xs text-muted-foreground mt-2">Checking RSS feeds every 30 seconds...</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
