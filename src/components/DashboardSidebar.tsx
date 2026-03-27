import { Video, FileText, MapPin, BarChart3, Shield, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

type Page = "live" | "reports" | "location" | "statistics";

const menuItems: { id: Page; label: string; icon: React.ElementType }[] = [
  { id: "live", label: "Live Feed", icon: Video },
  { id: "reports", label: "See Reports", icon: FileText },
  { id: "location", label: "Setup Location", icon: MapPin },
  { id: "statistics", label: "Statistics", icon: BarChart3 },
];

interface Props {
  activePage: Page;
  onPageChange: (page: Page) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export function DashboardSidebar({ activePage, onPageChange, isOpen, onToggle }: Props) {
  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={onToggle}
        className="fixed top-4 left-4 z-50 lg:hidden glass rounded-xl p-2 text-foreground"
      >
        {isOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-30 bg-background/60 lg:hidden" onClick={onToggle} />
      )}

      <aside
        className={cn(
          "fixed top-0 left-0 z-40 h-full w-64 glass-strong flex flex-col transition-transform duration-300",
          "lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand */}
        <div className="p-6 pb-2">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
              <Shield className="text-primary" size={22} />
            </div>
            <div>
              <h1 className="text-base font-semibold text-foreground leading-tight">Wildlife Intrusion</h1>
              <p className="text-xs text-muted-foreground">Detection System</p>
            </div>
          </div>
        </div>

        <div className="h-px bg-border/50 mx-4 my-2" />

        {/* Nav */}
        <nav className="flex-1 px-3 py-2 space-y-1">
          {menuItems.map((item) => {
            const active = activePage === item.id;
            return (
              <motion.button
                key={item.id}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => {
                  onPageChange(item.id);
                  if (window.innerWidth < 1024) onToggle();
                }}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-primary/15 text-primary sidebar-item-glow"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <item.icon size={18} />
                <span>{item.label}</span>
                {active && (
                  <motion.div
                    layoutId="sidebar-dot"
                    className="ml-auto w-2 h-2 rounded-full bg-primary"
                  />
                )}
              </motion.button>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
