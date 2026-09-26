"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FeatureContribution } from "@/lib/api";

const LABELS: Record<string, string> = {
  previous_gpa: "Previous GPA",
  previous_semester_gpa: "Previous Semester GPA",
  attendance_percentage: "Attendance %",
  quiz_avg: "Quiz Average",
  assignment_avg: "Assignment Average",
  midterm_score: "Midterm Score",
  project_score: "Project Score",
  lab_score: "Lab Score",
  completed_courses: "Completed Courses",
  credit_load: "Credit Load",
  historical_trend: "Historical Trend",
};

export function ExplanationChart({ contributions }: { contributions: FeatureContribution[] }) {
  const data = contributions
    .slice(0, 8)
    .map((c) => ({ name: LABELS[c.feature] ?? c.feature, value: c.contribution }))
    .sort((a, b) => a.value - b.value);

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => (typeof value === "number" ? value.toFixed(4) : value)} />
          <Bar dataKey="value" radius={4}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.value >= 0 ? "#059669" : "#dc2626"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-slate-500">
        Positive (green) bars pushed the prediction higher; negative (red) bars pushed it lower. These describe the
        model&apos;s behavior for this prediction only — they are not proof of real-world cause and effect.
      </p>
    </div>
  );
}
