import { useState } from "react";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { LiveFeedPage } from "@/components/LiveFeedPage";
import { ReportsPage } from "@/components/ReportsPage";
import { LocationPage } from "@/components/LocationPage";
import { StatisticsPage } from "@/components/StatisticsPage";

type Page = "live" | "reports" | "location" | "statistics";

const Index = () => {
  const [activePage, setActivePage] = useState<Page>("live");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Ambient gradient background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      </div>

      <DashboardSidebar
        activePage={activePage}
        onPageChange={setActivePage}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <main className="lg:ml-64 min-h-screen p-6 pt-16 lg:pt-6">
        <div className="max-w-[900px] mx-auto">
          {activePage === "live" && <LiveFeedPage />}
          {activePage === "reports" && <ReportsPage />}
          {activePage === "location" && <LocationPage />}
          {activePage === "statistics" && <StatisticsPage />}
        </div>
      </main>
    </div>
  );
};

export default Index;
