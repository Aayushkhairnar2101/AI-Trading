import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  ColorType
} from "lightweight-charts";
import { Maximize2, Radio, Clock } from "lucide-react";

export default function CandleChart({ candles, decisionCard, symbol = "BTCUSDT" }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const emaFastSeriesRef = useRef(null);
  const emaSlowSeriesRef = useRef(null);
  const slLineRef = useRef(null);
  const tpLineRef = useRef(null);
  const hasFittedRef = useRef(false);

  const [lastCandle, setLastCandle] = useState(null);
  const [updateTimestamp, setUpdateTimestamp] = useState(null);

  // 1. Initialize Chart ONCE on mount
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Clear any previous artifacts
    chartContainerRef.current.innerHTML = "";
    hasFittedRef.current = false;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#475569"
      },
      grid: {
        vertLines: { color: "#f1f5f9" },
        horzLines: { color: "#f1f5f9" }
      },
      width: chartContainerRef.current.clientWidth || 600,
      height: 420,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "#e2e8f0"
      },
      rightPriceScale: {
        borderColor: "#e2e8f0",
        autoScale: true
      }
    });

    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#059669",
      downColor: "#dc2626",
      borderVisible: false,
      wickUpColor: "#059669",
      wickDownColor: "#dc2626"
    });
    candleSeriesRef.current = candleSeries;

    // Volume series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#94a3b8",
      priceFormat: { type: "volume" },
      priceScaleId: "",
      scaleMargins: {
        top: 0.8,
        bottom: 0
      }
    });
    volumeSeriesRef.current = volumeSeries;

    // EMA 9 Series
    const emaFastSeries = chart.addSeries(LineSeries, {
      color: "#2563eb",
      lineWidth: 2,
      title: "EMA 9"
    });
    emaFastSeriesRef.current = emaFastSeries;

    // EMA 21 Series
    const emaSlowSeries = chart.addSeries(LineSeries, {
      color: "#f59e0b",
      lineWidth: 2,
      title: "EMA 21"
    });
    emaSlowSeriesRef.current = emaSlowSeries;

    // ResizeObserver for reliable container resizing
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length > 0 && chartRef.current) {
        const { width } = entries[0].contentRect;
        if (width > 0) {
          chartRef.current.applyOptions({ width });
        }
      }
    });

    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  // 2. Smoothly Update Data on existing Series when `candles` changes (WITHOUT rebuilding chart)
  useEffect(() => {
    if (!candleSeriesRef.current || !candles || candles.length === 0) return;

    try {
      // Deduplicate by integer seconds timestamp and sort ascending
      const candleMap = new Map();
      for (const c of candles) {
        const t = Math.floor(Number(c.time));
        if (!isNaN(t) && t > 0) {
          candleMap.set(t, {
            time: t,
            open: Number(c.open),
            high: Number(c.high),
            low: Number(c.low),
            close: Number(c.close),
            volume: Number(c.volume || 0),
            ema_fast:
              c.ema_fast !== undefined && c.ema_fast !== null && !isNaN(Number(c.ema_fast))
                ? Number(c.ema_fast)
                : null,
            ema_slow:
              c.ema_slow !== undefined && c.ema_slow !== null && !isNaN(Number(c.ema_slow))
                ? Number(c.ema_slow)
                : null
          });
        }
      }

      const sorted = Array.from(candleMap.values()).sort((a, b) => a.time - b.time);
      if (sorted.length === 0) return;

      // Update series data
      candleSeriesRef.current.setData(
        sorted.map((c) => ({
          time: c.time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close
        }))
      );

      volumeSeriesRef.current.setData(
        sorted.map((c) => ({
          time: c.time,
          value: c.volume,
          color: c.close >= c.open ? "#a7f3d0" : "#fecaca"
        }))
      );

      const emaFastData = sorted
        .filter((c) => c.ema_fast !== null)
        .map((c) => ({ time: c.time, value: c.ema_fast }));
      if (emaFastData.length > 0) {
        emaFastSeriesRef.current.setData(emaFastData);
      }

      const emaSlowData = sorted
        .filter((c) => c.ema_slow !== null)
        .map((c) => ({ time: c.time, value: c.ema_slow }));
      if (emaSlowData.length > 0) {
        emaSlowSeriesRef.current.setData(emaSlowData);
      }

      // Track latest candle for UI header
      const latest = sorted[sorted.length - 1];
      setLastCandle(latest);
      setUpdateTimestamp(new Date());

      // Fit content only on initial load so user zoom/scroll is preserved
      if (!hasFittedRef.current && chartRef.current && sorted.length > 0) {
        chartRef.current.timeScale().fitContent();
        hasFittedRef.current = true;
      }
    } catch (err) {
      console.error("CandleChart data update error:", err);
    }
  }, [candles]);

  // 3. Update Stop Loss & Take Profit Price Lines when `decisionCard` changes
  useEffect(() => {
    if (!candleSeriesRef.current) return;

    // Remove previous price lines if any
    if (slLineRef.current) {
      try {
        candleSeriesRef.current.removePriceLine(slLineRef.current);
      } catch (e) {}
      slLineRef.current = null;
    }
    if (tpLineRef.current) {
      try {
        candleSeriesRef.current.removePriceLine(tpLineRef.current);
      } catch (e) {}
      tpLineRef.current = null;
    }

    // Add Stop Loss line if valid
    if (decisionCard && decisionCard.proposed_stop_loss > 0) {
      slLineRef.current = candleSeriesRef.current.createPriceLine({
        price: decisionCard.proposed_stop_loss,
        color: "#dc2626",
        lineWidth: 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: "Stop Loss"
      });
    }

    // Add Take Profit line if valid
    if (decisionCard && decisionCard.proposed_take_profit > 0) {
      tpLineRef.current = candleSeriesRef.current.createPriceLine({
        price: decisionCard.proposed_take_profit,
        color: "#059669",
        lineWidth: 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: "Take Profit"
      });
    }
  }, [decisionCard]);

  const handleFitContent = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  };

  const isGreen = lastCandle ? lastCandle.close >= lastCandle.open : true;

  return (
    <div className="card" style={{ padding: "1rem" }}>
      <div
        className="card-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.5rem",
          flexWrap: "wrap",
          gap: "0.5rem"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: "1.05rem", fontWeight: 700 }}>
            {symbol} Candlestick Terminal
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              padding: "0.15rem 0.5rem",
              borderRadius: "4px",
              background: "#ecfdf5",
              color: "#065f46",
              border: "1px solid #a7f3d0",
              fontSize: "0.725rem",
              fontWeight: 600
            }}
          >
            <Radio size={12} color="#059669" className="spin-slow" />
            Live Testnet Feed (5m)
          </span>
          {lastCandle && (
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "1rem",
                fontWeight: 700,
                color: isGreen ? "#059669" : "#dc2626"
              }}
            >
              ${lastCandle.close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontSize: "0.75rem", color: "var(--text-light)" }}>
          {updateTimestamp && (
            <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <Clock size={12} />
              {updateTimestamp.toLocaleTimeString()}
            </span>
          )}
          <button
            className="btn btn-outline btn-sm"
            onClick={handleFitContent}
            title="Reset chart view to fit all loaded candles"
            style={{ padding: "0.2rem 0.5rem", fontSize: "0.725rem" }}
          >
            <Maximize2 size={12} /> Fit
          </button>
        </div>
      </div>

      <div style={{ fontSize: "0.725rem", color: "var(--text-light)", marginBottom: "0.5rem" }}>
        <span style={{ color: "#2563eb", fontWeight: 600 }}>■ EMA 9</span> &bull;{" "}
        <span style={{ color: "#f59e0b", fontWeight: 600 }}>■ EMA 21</span> &bull;{" "}
        <span>5m Closed Candles (Delta Exchange India Testnet Contract: BTCUSD)</span>
      </div>

      <div ref={chartContainerRef} style={{ width: "100%", height: "420px" }} />
    </div>
  );
}
