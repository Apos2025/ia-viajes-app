import React, { useMemo, useState } from "react";
import { format } from "date-fns";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";

/**
 * TripPlanner.jsx
 * - Selector de rango de fechas O "fechas flexibles" por mes + nº de días
 * - Envia al backend el payload { destination, dates, budget }
 *   * dates: "YYYY-MM-DD a YYYY-MM-DD" o "<N> dias en <mes> <año>"
 * - Muestra loading, errores y el itinerario recibido
 *
 * Requisitos:
 *   npm i react-day-picker date-fns
 */

const MONTHS_ES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

function toIso(d) {
  try {
    return format(d, "yyyy-MM-dd");
  } catch {
    return null;
  }
}

export default function TripPlanner() {
  const [destination, setDestination] = useState("");
  const [budget, setBudget] = useState("");

  // Rango de fechas clásico
  const [range, setRange] = useState({ from: undefined, to: undefined });

  // Fechas flexibles
  const [flexible, setFlexible] = useState(false);
  const [flexMonth, setFlexMonth] = useState(new Date().getMonth());
  const [flexYear, setFlexYear] = useState(new Date().getFullYear());
  const [flexDays, setFlexDays] = useState(14);

  // Estado de UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [itinerary, setItinerary] = useState("");
  const [daysInferred, setDaysInferred] = useState(null);

  const canSubmit = useMemo(() => {
    if (!destination.trim()) return false;
    if (flexible) return flexDays >= 1 && flexDays <= 30;
    return Boolean(range.from && range.to);
  }, [destination, flexible, flexDays, range]);

  function composeDatesField() {
    if (flexible) {
      const monthName = MONTHS_ES[flexMonth];
      return `${flexDays} dias en ${monthName} ${flexYear}`;
    }
    const a = toIso(range.from);
    const b = toIso(range.to);
    return a && b ? `${a} a ${b}` : "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setItinerary("");

    const datesText = composeDatesField();
    if (!datesText) {
      setError("Selecciona una fecha válida o activa fechas flexibles.");
      return;
    }

    const payload = {
      destination: destination.trim(),
      dates: datesText,
      budget: budget ? Number(budget) : null,
    };

    try {
      setLoading(true);
      // Si configuraste rewrites en vercel.json, puedes usar "/api/generate-trip"
      // De lo contrario, pon aquí tu URL de Render completa:
      // const API = "https://TU-SERVICIO.onrender.com/api/generate-trip";
      const res = await fetch("/api/generate-trip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setItinerary(data.itinerary || "");
      setDaysInferred(typeof data.days_inferred === "number" ? data.days_inferred : null);
    } catch (err) {
      setError(err.message || "Error desconocido generando el itinerario");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl md:text-3xl font-bold mb-4">Planificador de Viajes</h1>
        <p className="text-sm text-slate-600 mb-6">
          Elige destino y fechas. Puedes usar <strong>rango de fechas</strong> o activar
          <strong> fechas flexibles</strong> por mes y número de días.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6 bg-white rounded-2xl shadow p-5">
          <div className="grid md:grid-cols-2 gap-4">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium">Destino</span>
              <input
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="Ej: Tokio, París, México…"
                className="border rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium">Presupuesto total (€)</span>
              <input
                type="number"
                min={0}
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="Opcional"
                className="border rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              id="flexible"
              type="checkbox"
              checked={flexible}
              onChange={(e) => setFlexible(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="flexible" className="text-sm">
              Usar <strong>fechas flexibles</strong> por mes
            </label>
          </div>

          {!flexible ? (
            <div>
              <p className="text-sm mb-2 font-medium">Rango de fechas</p>
              <DayPicker
                mode="range"
                selected={range}
                onSelect={setRange}
                numberOfMonths={2}
                weekStartsOn={1}
              />
            </div>
          ) : (
            <div className="grid md:grid-cols-3 gap-4">
              <label className="flex flex-col gap-1">
                <span className="text-sm font-medium">Mes</span>
                <select
                  value={flexMonth}
                  onChange={(e) => setFlexMonth(Number(e.target.value))}
                  className="border rounded-xl px-3 py-2"
                >
                  {MONTHS_ES.map((m, i) => (
                    <option key={m} value={i}>{m}</option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-sm font-medium">Año</span>
                <input
                  type="number"
                  value={flexYear}
                  onChange={(e) => setFlexYear(Number(e.target.value))}
                  className="border rounded-xl px-3 py-2"
                  min={new Date().getFullYear()}
                  max={new Date().getFullYear() + 2}
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-sm font-medium">Número de días</span>
                <input
                  type="number"
                  value={flexDays}
                  onChange={(e) => setFlexDays(Number(e.target.value))}
                  className="border rounded-xl px-3 py-2"
                  min={1}
                  max={30}
                />
              </label>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={!canSubmit || loading}
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white disabled:opacity-60 disabled:cursor-not-allowed hover:bg-indigo-700 transition"
            >
              {loading ? "Generando…" : "Crear itinerario"}
            </button>
            {daysInferred != null && (
              <span className="text-xs text-slate-600">Días detectados por el backend: <b>{daysInferred}</b></span>
            )}
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-50 text-red-700 text-sm">{error}</div>
          )}
        </form>

        {itinerary && (
          <div className="mt-6 bg-white rounded-2xl shadow p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Itinerario</h2>
              <button
                onClick={() => navigator.clipboard.writeText(itinerary)}
                className="text-sm px-3 py-1 rounded-lg border hover:bg-slate-50"
              >
                Copiar
              </button>
            </div>
            <pre className="whitespace-pre-wrap text-sm leading-6">{itinerary}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
