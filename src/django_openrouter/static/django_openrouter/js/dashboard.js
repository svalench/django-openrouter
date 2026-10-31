"use strict";

// Фильтры и графики дашборда. Данные графиков приходят из json_script, без inline-скрипта.

function bindDashboardFilters() {
    const form = document.getElementById("or-dashboard-filters");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    form.querySelectorAll("[data-auto-submit]").forEach((control) => {
        control.addEventListener("change", () => {
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
                return;
            }
            form.submit();
        });
    });
}

function cssColor(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

function themeColors() {
    return {
        fg: cssColor("--body-fg", "#333333"),
        quiet: cssColor("--body-quiet-color", "#666666"),
        grid: cssColor("--hairline-color", "#e8e8e8"),
        bg: cssColor("--body-bg", "#ffffff"),
        font: cssColor("--font-family-primary", "Segoe UI, system-ui, sans-serif"),
    };
}

function hexToRgba(hex, alpha) {
    const raw = hex.replace("#", "");
    const expanded = raw.length === 3 ? raw.split("").map((ch) => ch + ch).join("") : raw;
    const value = Number.parseInt(expanded, 16);
    if (!Number.isFinite(value) || expanded.length !== 6) {
        return hex;
    }
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function formatChartValue(value, unit) {
    if (value == null || Number.isNaN(value)) {
        return "—";
    }
    if (unit === "usd") {
        const abs = Math.abs(value);
        const digits = abs > 0 && abs < 0.01 ? 4 : 2;
        return `$${value.toLocaleString(undefined, {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits,
        })}`;
    }
    if (unit === "percent") {
        return `${value.toFixed(1)}%`;
    }
    if (unit === "ms") {
        return `${Math.round(value).toLocaleString()} ms`;
    }
    return Math.round(value).toLocaleString();
}

function pointValue(context, kind) {
    const parsed = context.parsed;
    if (!parsed) {
        return null;
    }
    const value = kind === "bar" ? parsed.x : parsed.y;
    return typeof value === "number" ? value : null;
}

function buildChartConfig(spec, colors) {
    const kind = spec.kind === "bar" ? "bar" : "line";
    const manyPoints = Array.isArray(spec.labels) && spec.labels.length > 36;
    const datasets = (spec.datasets || []).map((dataset) => {
        const color = dataset.color || "#3b82f6";
        return {
            label: dataset.label,
            data: dataset.data,
            borderColor: color,
            backgroundColor: hexToRgba(color, kind === "line" ? 0.16 : 0.88),
            fill: kind === "line",
            tension: 0.35,
            borderWidth: 2,
            pointRadius: kind === "line" && !manyPoints ? 3 : 0,
            pointHoverRadius: 5,
            pointBackgroundColor: color,
            spanGaps: false,
            borderRadius: kind === "bar" ? 4 : 0,
        };
    });
    return {
        type: kind,
        data: { labels: spec.labels || [], datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: kind === "bar" ? "y" : "x",
            interaction: kind === "line"
                ? { mode: "index", intersect: false }
                : { mode: "nearest", intersect: true },
            plugins: {
                legend: {
                    display: datasets.length > 1,
                    position: "bottom",
                    labels: {
                        color: colors.fg,
                        boxWidth: 8,
                        boxHeight: 8,
                        usePointStyle: true,
                        pointStyle: "circle",
                        padding: 14,
                        font: { family: colors.font, size: 12 },
                    },
                },
                tooltip: {
                    backgroundColor: colors.fg,
                    titleColor: colors.bg,
                    bodyColor: colors.bg,
                    padding: 10,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label(context) {
                            const value = pointValue(context, kind);
                            const formatted = formatChartValue(value, spec.unit);
                            return `${context.dataset.label}: ${formatted}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: kind === "bar",
                    grid: { color: colors.grid },
                    border: { display: false },
                    ticks: {
                        color: colors.quiet,
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: kind === "bar" ? 6 : 8,
                        font: { family: colors.font, size: 11 },
                        callback(value) {
                            if (kind !== "bar") {
                                return this.getLabelForValue(value);
                            }
                            return formatChartValue(Number(value), spec.unit);
                        },
                    },
                },
                y: {
                    beginAtZero: true,
                    grace: kind === "line" ? "8%" : 0,
                    grid: { color: colors.grid },
                    border: { display: false },
                    ticks: {
                        color: colors.quiet,
                        font: { family: colors.font, size: 11 },
                        callback(value) {
                            if (kind === "bar") {
                                return this.getLabelForValue(value);
                            }
                            return formatChartValue(Number(value), spec.unit);
                        },
                    },
                },
            },
        },
    };
}

const dashboardCharts = [];

function drawDashboardCharts() {
    while (dashboardCharts.length) {
        const chart = dashboardCharts.pop();
        chart.destroy();
    }
    const node = document.getElementById("or-dashboard-charts");
    if (!node || typeof Chart === "undefined") {
        return;
    }
    let payload;
    try {
        payload = JSON.parse(node.textContent || "{}");
    } catch (error) {
        return;
    }
    const colors = themeColors();
    document.querySelectorAll("canvas.or-chart").forEach((canvas) => {
        const spec = payload[canvas.dataset.chartId];
        if (!spec) {
            return;
        }
        dashboardCharts.push(new Chart(canvas, buildChartConfig(spec, colors)));
    });
}

function observeDashboardTheme() {
    const observer = new MutationObserver(() => {
        drawDashboardCharts();
    });
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    if (typeof media.addEventListener === "function") {
        media.addEventListener("change", () => {
            drawDashboardCharts();
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    bindDashboardFilters();
    drawDashboardCharts();
    observeDashboardTheme();
});
