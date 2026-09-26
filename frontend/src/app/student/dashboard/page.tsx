"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, clearTokens, PredictionResponse, UserOut } from "@/lib/api";
import { RiskBadge } from "@/components/RiskBadge";
import { ExplanationChart } from "@/components/ExplanationChart";

export default function StudentDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [studentIdInput, setStudentIdInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  async function requestPrediction() {
    const studentId = Number(studentIdInput);
    if (!studentId) {
      setError("Enter your numeric student profile ID (ask an administrator if you don't know it).");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const result = await api.generatePrediction(studentId);
      setPrediction(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate a prediction.");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Student Dashboard</h1>
          {user && <p className="text-sm text-slate-500">Signed in as {user.name}</p>}
        </div>
        <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-900">
          Sign out
        </button>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Get your performance prediction</h2>
          <p className="mt-1 text-sm text-slate-500">
            This generates a fresh, model-based estimate from your current academic data.
          </p>
          <div className="mt-4 flex gap-2">
            <input
              value={studentIdInput}
              onChange={(e) => setStudentIdInput(e.target.value)}
              placeholder="Your student profile ID"
              className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
            />
            <button
              onClick={requestPrediction}
              disabled={loading}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {loading ? "Generating…" : "Generate prediction"}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>

        {prediction && (
          <>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">Predicted GPA (estimate)</p>
                <p className="mt-1 text-3xl font-bold text-slate-900">{prediction.regression.predicted_gpa.toFixed(2)}</p>
                <p className="mt-1 text-xs text-slate-400">Model: {prediction.regression.model_version}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">Performance category (estimate)</p>
                <div className="mt-2 flex items-center gap-3">
                  <span className="text-xl font-semibold text-slate-900">{prediction.classification.predicted_category}</span>
                  <RiskBadge level={prediction.classification.risk_level} />
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  Confidence: {(prediction.classification.confidence * 100).toFixed(0)}% · Model:{" "}
                  {prediction.classification.model_version}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-base font-semibold text-slate-900">What influenced this estimate</h3>
              <p className="text-sm text-slate-500">Feature contributions for the performance-category prediction.</p>
              <div className="mt-4">
                <ExplanationChart contributions={prediction.classification.explanation} />
              </div>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              {prediction.disclaimer}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
