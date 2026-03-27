import { motion } from "framer-motion";
import { useEffect, useState } from "react";

type ReportItem = {
  timestamp: string;
  type: string;
  confidence: number;
  user_response: string;
  report_path: string;
};

export function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([]);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/reports")
      .then((res) => res.json())
      .then((data: ReportItem[]) => {
        const sorted = [...data].reverse();
        setReports(sorted);
      })
      .catch((err) => console.error("Fetch error:", err));
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-2xl font-bold text-foreground">Detection Reports</h2>
        <p className="text-sm text-muted-foreground mt-1">View historical intrusion events</p>
      </div>

      <div className="reports-container">
        {reports.length === 0 ? (
          <p className="no-reports">No reports available yet</p>
        ) : (
          reports.map((report, index) => (
            <div key={index} className="report-card">
              <div className="report-header">
                <h3>{report.type}</h3>
                <span className={`status ${report.user_response === "Confirmed" ? "confirmed" : "pending"}`}>
                  {report.user_response}
                </span>
              </div>

              <p>
                <strong>Time:</strong> {report.timestamp}
              </p>
              <p>
                <strong>Confidence:</strong> {(Number(report.confidence) * 100).toFixed(1)}%
              </p>

              <a
                href={`http://127.0.0.1:5000/download/${report.report_path}`}
                target="_blank"
                rel="noopener noreferrer"
                className="download-btn"
              >
                📄 Download PDF
              </a>
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
}
