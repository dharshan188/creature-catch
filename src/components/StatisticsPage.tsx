import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const data = [
  { name: "Human", count: 24, color: "hsl(0, 80%, 55%)" },
  { name: "Elephant", count: 18, color: "hsl(30, 90%, 55%)" },
  { name: "Bear", count: 7, color: "hsl(270, 60%, 55%)" },
  { name: "Giraffe", count: 12, color: "hsl(50, 90%, 55%)" },
];

const weeklyData = [
  { day: "Mon", detections: 8 },
  { day: "Tue", detections: 14 },
  { day: "Wed", detections: 6 },
  { day: "Thu", detections: 22 },
  { day: "Fri", detections: 11 },
  { day: "Sat", detections: 3 },
  { day: "Sun", detections: 5 },
];

export function StatisticsPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-2xl font-bold text-foreground">Statistics</h2>
        <p className="text-sm text-muted-foreground mt-1">Detection analytics and insights</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {data.map((item) => (
          <div key={item.name} className="glass rounded-xl p-4">
            <p className="text-xs text-muted-foreground">{item.name}</p>
            <p className="text-2xl font-bold text-foreground mt-1">{item.count}</p>
            <p className="text-xs mt-1" style={{ color: item.color }}>detections</p>
          </div>
        ))}
      </div>

      {/* Bar chart - by type */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Detections by Type</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data}>
            <XAxis dataKey="name" tick={{ fill: "hsl(220, 10%, 55%)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "hsl(220, 10%, 55%)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "hsl(220, 20%, 12%)",
                border: "1px solid hsl(220, 15%, 25%)",
                borderRadius: "12px",
                color: "hsl(220, 20%, 95%)",
              }}
            />
            <Bar dataKey="count" radius={[8, 8, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Weekly trend */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Weekly Trend</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={weeklyData}>
            <XAxis dataKey="day" tick={{ fill: "hsl(220, 10%, 55%)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "hsl(220, 10%, 55%)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "hsl(220, 20%, 12%)",
                border: "1px solid hsl(220, 15%, 25%)",
                borderRadius: "12px",
                color: "hsl(220, 20%, 95%)",
              }}
            />
            <Bar dataKey="detections" fill="hsl(200, 100%, 50%)" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
