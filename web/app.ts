interface SimSettings {
  n_input: number;
  n_hidden: number;
  n_output: number;
  n_steps: number;
  neuron_type: string;
  learn: boolean;
  seed: number;
  input_pattern: number[];
}

interface SimResult {
  ok: boolean;
  error?: string;
  settings?: SimSettings;
  input_counts?: number[];
  hidden_counts?: number[];
  output_counts?: number[];
  input_spikes?: number[][];
  hidden_spikes?: number[][];
  output_spikes?: number[][];
  hidden_voltage?: number[][];
  output_voltage?: number[][];
  input_weights?: number[][];
  output_weights?: number[][];
  initial_input_weights?: number[][];
  initial_output_weights?: number[][];
  pre_trace?: number[][];
  post_trace?: number[][];
  elapsed_ms?: number;
  honesty?: string;
}

interface StatusResult {
  ok: boolean;
  version?: string;
  runs?: number;
}

type LayerName = "input" | "hidden" | "output";

function byId(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error("missing element: " + id);
  return el;
}

function inputOf(id: string): HTMLInputElement {
  return byId(id) as HTMLInputElement;
}

function selectOf(id: string): HTMLSelectElement {
  return byId(id) as HTMLSelectElement;
}

function canvasOf(id: string): HTMLCanvasElement {
  return byId(id) as HTMLCanvasElement;
}

function num(id: string, fallback: number, lo: number, hi: number): number {
  const raw = inputOf(id).value.trim();
  if (raw === "") return fallback;
  const v = parseInt(raw, 10);
  if (Number.isNaN(v)) return fallback;
  return Math.max(lo, Math.min(hi, v));
}

let lastResult: SimResult | null = null;
let currentStep = 0;
let playTimer: number | null = null;
let selectedLayer: LayerName = "hidden";
let selectedNeuron = 0;
let voltageLayer: "hidden" | "output" = "hidden";
let voltageNeuron = 0;

function readPattern(nInput: number, raw: string): number[] {
  const parts = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (parts.length === 0) throw new Error("الگوی ورودی خالی است");
  if (parts.length !== nInput)
    throw new Error(`الگوی ورودی باید دقیقاً ${String(nInput)} مقدار داشته باشد (اکنون ${String(parts.length)})`);
  return parts.map((p, i) => {
    const v = parseFloat(p);
    if (!Number.isFinite(v)) throw new Error(`مقدار ${String(i + 1)} الگو عدد متناهی نیست: ${p}`);
    return v;
  });
}

function readSettings(): SimSettings {
  const nInput = num("nInput", 4, 1, 32);
  const patternRaw = inputOf("pattern").value;
  const pattern = readPattern(nInput, patternRaw);
  return {
    n_input: nInput,
    n_hidden: num("nHidden", 6, 1, 128),
    n_output: num("nOutput", 2, 1, 32),
    n_steps: num("nSteps", 200, 10, 2000),
    neuron_type: selectOf("neuronType").value || "lif",
    learn: (byId("learn") as HTMLInputElement).checked,
    seed: num("seed", 42, 0, 2147483647),
    input_pattern: pattern,
  };
}

function setStatus(msg: string, state: "" | "ok" | "error"): void {
  const el = byId("status");
  el.textContent = msg;
  el.setAttribute("data-state", state);
}

function setFormError(msg: string): void {
  const el = byId("formError");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.textContent = msg;
  el.hidden = false;
}

async function refreshStatus(): Promise<void> {
  try {
    const res = await fetch("/api/status");
    const data = (await res.json()) as StatusResult;
    if (data.ok) {
      const ver = byId("ver");
      if (ver) ver.textContent = "v" + (data.version ?? "?");
      const runs = byId("runs");
      if (runs) runs.textContent = "اجراها: " + String(data.runs ?? 0);
    }
  } catch {
    setStatus("عدم دسترسی به سرور", "error");
  }
}

function ensureHiDPI(c: HTMLCanvasElement): CanvasRenderingContext2D | null {
  const ctx = c.getContext("2d");
  if (!ctx) return null;
  const dpr = window.devicePixelRatio || 1;
  const rect = c.getBoundingClientRect();
  const w = Math.round(rect.width * dpr);
  const h = Math.round(rect.height * dpr);
  if (c.width !== w || c.height !== h) {
    c.width = w;
    c.height = h;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function clearCanvas(c: HTMLCanvasElement, fill = "#0c1421"): void {
  const ctx = c.getContext("2d");
  if (!ctx) return;
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = fill;
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.restore();
}

async function run(ev?: Event): Promise<void> {
  if (ev) ev.preventDefault();
  setFormError("");
  let settings: SimSettings;
  try {
    settings = readSettings();
  } catch (e) {
    setFormError(String(e instanceof Error ? e.message : e));
    setStatus("ورودی نامعتبر", "error");
    return;
  }
  const btn = byId("runBtn") as HTMLButtonElement;
  const fieldset = byId("settingsFields") as HTMLFieldSetElement;
  btn.disabled = true;
  fieldset.disabled = true;
  setStatus("در حال اجرا…", "");
  try {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    const data = (await res.json()) as SimResult;
    if (!data.ok) {
      setStatus("خطا: " + (data.error ?? "نامشخص"), "error");
      setFormError(data.error ?? "خطای سرور");
      return;
    }
    lastResult = data;
    currentStep = 0;
    selectedLayer = "hidden";
    selectedNeuron = 0;
    voltageLayer = "hidden";
    voltageNeuron = 0;
    (byId("exportBtn") as HTMLButtonElement).disabled = false;
    setupAfterResult(data);
    drawAll(data);
    setStatus("انجام شد در " + String(data.elapsed_ms ?? 0) + " میلی‌ثانیه", "ok");
    void refreshStatus();
  } catch (e) {
    setStatus("خطای شبکه: " + String(e), "error");
  } finally {
    btn.disabled = false;
    fieldset.disabled = false;
  }
}

function setupAfterResult(d: SimResult): void {
  if (!d.settings) return;
  const s = d.settings;
  byId("networkSummary").textContent = `I ${String(s.n_input)} · H ${String(s.n_hidden)} · O ${String(s.n_output)} · گام ${String(s.n_steps)} · ${s.neuron_type}${s.learn ? " · STDP" : ""}`;
  byId("modelBadge").textContent = s.neuron_type;
  const honesty = byId("honesty");
  if (honesty && d.honesty) {
    honesty.textContent = d.honesty;
    honesty.hidden = false;
  }
  const slider = inputOf("stepSlider");
  slider.min = "0";
  slider.max = String(Math.max(0, s.n_steps - 1));
  slider.value = "0";
  slider.disabled = false;
  (byId("playBtn") as HTMLButtonElement).disabled = false;
  byId("stepLabel").textContent = `۰ / ${String(s.n_steps - 1)}`;
  populateInspectorSelects(s);
  populateVoltageSelects(s);
  const weightMode = selectOf("weightMode");
  weightMode.disabled = false;
  (byId("voltageLayer") as HTMLSelectElement).disabled = false;
  (byId("inspectLayer") as HTMLSelectElement).disabled = false;
  stopPlayback();
}

function populateInspectorSelects(s: SimSettings): void {
  const layerSel = selectOf("inspectLayer");
  const neuronSel = selectOf("inspectNeuron");
  layerSel.disabled = false;
  neuronSel.disabled = false;
  layerSel.value = selectedLayer;
  rebuildNeuronOptions(neuronSel, selectedLayer, s);
  neuronSel.value = String(selectedNeuron);
}

function populateVoltageSelects(s: SimSettings): void {
  const layerSel = selectOf("voltageLayer");
  const neuronSel = selectOf("voltageNeuron");
  layerSel.value = voltageLayer;
  rebuildNeuronOptions(neuronSel, voltageLayer === "hidden" ? "hidden" : "output", s);
  neuronSel.value = String(voltageNeuron);
}

function rebuildNeuronOptions(sel: HTMLSelectElement, layer: LayerName, s: SimSettings): void {
  const count = layer === "input" ? s.n_input : layer === "hidden" ? s.n_hidden : s.n_output;
  sel.innerHTML = "";
  for (let i = 0; i < count; i++) {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = `${layer} ${String(i)}`;
    sel.appendChild(opt);
  }
}

function drawAll(d: SimResult): void {
  drawTopology(d, currentStep);
  drawRaster(d);
  drawVoltage(d);
  drawHeatmaps(d);
  drawStats(d);
  updateInspection();
  updateVoltageSummary();
}

function drawStats(d: SimResult): void {
  const host = byId("stats");
  if (!d.settings) {
    host.innerHTML = "";
    return;
  }
  const totalIn = (d.input_counts ?? []).reduce((a, b) => a + b, 0);
  const totalHid = (d.hidden_counts ?? []).reduce((a, b) => a + b, 0);
  const totalOut = (d.output_counts ?? []).reduce((a, b) => a + b, 0);
  const rateOut = d.settings.n_steps > 0 ? (totalOut / (d.settings.n_output * d.settings.n_steps)) : 0;
  const stats: Array<[string, string]> = [
    ["ورودی · کل اسپایک", String(totalIn)],
    ["پنهان · کل اسپایک", String(totalHid)],
    ["خروجی · کل اسپایک", String(totalOut)],
    ["نرخ خروجی", rateOut.toFixed(3)],
  ];
  host.innerHTML = stats
    .map(([k, v]) => `<dl class="stat"><dt>${k}</dt><dd>${v}</dd></dl>`)
    .join("");
}

type NodePos = { x: number; y: number; layer: LayerName; idx: number };

let cachedNodes: NodePos[] = [];
let cachedEdgesIn: Array<{ from: number; to: number; w: number }> = [];
let cachedEdgesOut: Array<{ from: number; to: number; w: number }> = [];

function computeLayout(s: SimSettings, rect: DOMRect): { nodes: NodePos[]; edgesIn: typeof cachedEdgesIn; edgesOut: typeof cachedEdgesOut } {
  const pad = 24;
  const colX = [pad + 34, rect.width / 2, rect.width - pad - 34];
  const nodes: NodePos[] = [];
  const layers: Array<{ name: LayerName; count: number; x: number }> = [
    { name: "input", count: s.n_input, x: colX[0] as number },
    { name: "hidden", count: s.n_hidden, x: colX[1] as number },
    { name: "output", count: s.n_output, x: colX[2] as number },
  ];
  for (const layer of layers) {
    const gap = (rect.height - 60) / Math.max(1, layer.count);
    for (let i = 0; i < layer.count; i++) {
      nodes.push({ x: layer.x, y: 30 + gap * (i + 0.5), layer: layer.name, idx: i });
    }
  }
  return { nodes, edgesIn: [], edgesOut: [] };
}

function drawTopology(d: SimResult, step: number): void {
  const canvas = canvasOf("topology");
  const ctx = ensureHiDPI(canvas);
  if (!ctx || !d.settings) {
    clearCanvas(canvas);
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const s = d.settings;
  const wIn = d.input_weights ?? [];
  const wOut = d.output_weights ?? [];

  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = "#0c1421";
  ctx.fillRect(0, 0, rect.width, rect.height);

  const layout = computeLayout(s, rect);
  cachedNodes = layout.nodes;

  const inputNodes = cachedNodes.filter((n) => n.layer === "input");
  const hiddenNodes = cachedNodes.filter((n) => n.layer === "hidden");
  const outputNodes = cachedNodes.filter((n) => n.layer === "output");

  const inpSpikes = d.input_spikes?.[step] ?? [];
  const hidSpikes = d.hidden_spikes?.[step] ?? [];
  const outSpikes = d.output_spikes?.[step] ?? [];

  const maxWIn = Math.max(0.0001, ...wIn.flat().map((v) => Math.abs(v)));
  const maxWOut = Math.max(0.0001, ...wOut.flat().map((v) => Math.abs(v)));

  function drawEdges(
    fromNodes: NodePos[],
    toNodes: NodePos[],
    weights: number[][],
    maxW: number,
    onlyFor: { layer: LayerName; idx: number } | null,
  ): void {
    if (!ctx) return;
    for (let i = 0; i < fromNodes.length; i++) {
      for (let j = 0; j < toNodes.length; j++) {
        const w = weights[i]?.[j] ?? 0;
        if (onlyFor) {
          const isFrom = onlyFor.layer === fromNodes[i]?.layer && onlyFor.idx === fromNodes[i]?.idx;
          const isTo = onlyFor.layer === toNodes[j]?.layer && onlyFor.idx === toNodes[j]?.idx;
          if (!isFrom && !isTo) continue;
        } else {
          if (Math.abs(w) < maxW * 0.15) continue;
        }
        const a = 0.18 + (Math.abs(w) / maxW) * 0.72;
        ctx.strokeStyle = w >= 0 ? `rgba(102,198,255,${String(a)})` : `rgba(255,190,123,${String(a)})`;
        ctx.lineWidth = 0.6 + (Math.abs(w) / maxW) * 2.2;
        ctx.beginPath();
        const p0 = fromNodes[i] as NodePos;
        const p1 = toNodes[j] as NodePos;
        const mx = (p0.x + p1.x) / 2;
        ctx.moveTo(p0.x + 14, p0.y);
        ctx.bezierCurveTo(mx, p0.y, mx, p1.y, p1.x - 14, p1.y);
        ctx.stroke();
      }
    }
  }

  const sel = lastResult ? { layer: selectedLayer, idx: selectedNeuron } : null;
  if (wIn.length && hiddenNodes.length) drawEdges(inputNodes, hiddenNodes, wIn, maxWIn, sel && (sel.layer === "input" || sel.layer === "hidden") ? sel : null);
  if (wOut.length && outputNodes.length) drawEdges(hiddenNodes, outputNodes, wOut, maxWOut, sel && (sel.layer === "hidden" || sel.layer === "output") ? sel : null);
  if (!sel) {
    if (wIn.length) drawEdges(inputNodes, hiddenNodes, wIn, maxWIn, null);
    if (wOut.length) drawEdges(hiddenNodes, outputNodes, wOut, maxWOut, null);
  }

  const nodeRadius = 13;
  for (const n of cachedNodes) {
    const spikes =
      n.layer === "input" ? (inpSpikes[n.idx] ?? 0) : n.layer === "hidden" ? (hidSpikes[n.idx] ?? 0) : (outSpikes[n.idx] ?? 0);
    const isSel = n.layer === selectedLayer && n.idx === selectedNeuron;
    ctx.beginPath();
    ctx.arc(n.x, n.y, nodeRadius + (spikes ? 3 : 0), 0, Math.PI * 2);
    if (n.layer === "input") ctx.fillStyle = spikes ? "#c9b3ff" : "#8a6fd8";
    else if (n.layer === "hidden") ctx.fillStyle = spikes ? "#8fe2ff" : "#4faed6";
    else ctx.fillStyle = spikes ? "#ffd9a6" : "#d99a4a";
    if (isSel) {
      ctx.shadowColor = "#60dfca";
      ctx.shadowBlur = 10;
    } else ctx.shadowBlur = 0;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = isSel ? "#60dfca" : "rgba(255,255,255,0.12)";
    ctx.lineWidth = isSel ? 2 : 1;
    ctx.stroke();
    ctx.fillStyle = "#0c1421";
    ctx.font = "700 10px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(n.idx), n.x, n.y + 0.5);
    ctx.fillStyle = n.layer === "input" ? "#ba9bff" : n.layer === "hidden" ? "#66c6ff" : "#ffbe7b";
    ctx.font = "10px Tahoma";
    ctx.fillText(n.layer[0] as string, n.x, n.y + 22);
  }

  ctx.fillStyle = "#9eafc5";
  ctx.font = "11px Tahoma";
  ctx.textAlign = "left";
  ctx.fillText(`گام ${String(step)} / ${String(s.n_steps - 1)}`, 10, rect.height - 8);
  ctx.textAlign = "right";
  ctx.fillText("صرفاً دادهٔ اندازه‌گیری‌شده", rect.width - 10, rect.height - 8);
}

function hitNode(x: number, y: number): NodePos | null {
  for (const n of cachedNodes) {
    const dx = x - n.x;
    const dy = y - n.y;
    if (dx * dx + dy * dy < 18 * 18) return n;
  }
  return null;
}

function drawRaster(d: SimResult): void {
  const canvas = canvasOf("raster");
  const ctx = ensureHiDPI(canvas);
  if (!ctx || !d.settings || !d.input_spikes || !d.hidden_spikes || !d.output_spikes) {
    clearCanvas(canvas);
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const s = d.settings;
  const steps = s.n_steps;
  const totalRows = s.n_input + s.n_hidden + s.n_output;
  const left = 44, right = 12, top = 14, bottom = 22;
  const plotW = rect.width - left - right;
  const plotH = rect.height - top - bottom;
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = "#0c1421";
  ctx.fillRect(0, 0, rect.width, rect.height);

  ctx.strokeStyle = "#1e2e44";
  ctx.lineWidth = 1;
  ctx.strokeRect(left, top, plotW, plotH);

  const rowH = plotH / totalRows;
  const colW = plotW / Math.max(1, steps);

  ctx.fillStyle = "#6b7f98";
  ctx.font = "10px Tahoma";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let r = 0; r < totalRows; r++) {
    const y = top + r * rowH + rowH / 2;
    let label = "";
    if (r < s.n_input) label = `I${String(r)}`;
    else if (r < s.n_input + s.n_hidden) label = `H${String(r - s.n_input)}`;
    else label = `O${String(r - s.n_input - s.n_hidden)}`;
    ctx.fillText(label, left - 6, y);
    if (r % 2 === 0) {
      ctx.fillStyle = "rgba(255,255,255,0.02)";
      ctx.fillRect(left, top + r * rowH, plotW, rowH);
      ctx.fillStyle = "#6b7f98";
    }
  }

  ctx.fillStyle = "#9eafc5";
  ctx.font = "10px Consolas, monospace";
  ctx.textAlign = "left";
  ctx.fillText("۰", left, rect.height - 4);
  ctx.textAlign = "right";
  ctx.fillText(String(steps - 1), left + plotW, rect.height - 4);
  ctx.textAlign = "center";
  ctx.fillText("گام", left + plotW / 2, rect.height - 4);

  const layers: Array<{ spikes: number[][]; offset: number; color: string }> = [
    { spikes: d.input_spikes, offset: 0, color: "#ba9bff" },
    { spikes: d.hidden_spikes, offset: s.n_input, color: "#66c6ff" },
    { spikes: d.output_spikes, offset: s.n_input + s.n_hidden, color: "#ffbe7b" },
  ];
  for (const layer of layers) {
    ctx.fillStyle = layer.color;
    for (let t = 0; t < layer.spikes.length; t++) {
      const row = layer.spikes[t] as number[];
      const x = left + t * colW;
      const w = Math.max(1, colW * 0.9);
      for (let u = 0; u < row.length; u++) {
        if (row[u]) {
          const y = top + (layer.offset + u) * rowH + 1;
          ctx.fillRect(x, y, w, Math.max(2, rowH - 2));
        }
      }
    }
  }

  if (lastResult) {
    const x = left + currentStep * colW;
    ctx.strokeStyle = "rgba(96,223,202,0.85)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  const sumIn = (d.input_counts ?? []).reduce((a, b) => a + b, 0);
  const sumHid = (d.hidden_counts ?? []).reduce((a, b) => a + b, 0);
  const sumOut = (d.output_counts ?? []).reduce((a, b) => a + b, 0);
  byId("rasterSummary").textContent =
    `ورودی ${String(sumIn)} · پنهان ${String(sumHid)} · خروجی ${String(sumOut)} — هر نقطه یک اسپایک ثبت‌شده در همان گام است؛ خط چین گام جاری بازپخش را نشان می‌دهد.`;
}

function drawVoltage(d: SimResult): void {
  const canvas = canvasOf("voltage");
  const ctx = ensureHiDPI(canvas);
  if (!ctx || !d.settings) {
    clearCanvas(canvas);
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const s = d.settings;
  const traces = voltageLayer === "hidden" ? d.hidden_voltage : d.output_voltage;
  if (!traces || traces.length === 0 || !traces[0]) {
    clearCanvas(canvas);
    byId("voltageSummary").textContent = "برای این مدل ولتاژ در دسترس نیست.";
    return;
  }
  const left = 48, right = 12, top = 14, bottom = 26;
  const plotW = rect.width - left - right;
  const plotH = rect.height - top - bottom;
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = "#0c1421";
  ctx.fillRect(0, 0, rect.width, rect.height);

  const idx = Math.min(voltageNeuron, (traces[0].length ?? 1) - 1);
  const vals = traces.map((row) => row[idx] as number);
  let vmin = Math.min(...vals), vmax = Math.max(...vals);
  if (!Number.isFinite(vmin) || !Number.isFinite(vmax)) {
    clearCanvas(canvas);
    return;
  }
  if (vmax - vmin < 1e-6) {
    vmin -= 0.5;
    vmax += 0.5;
  }
  const pad = (vmax - vmin) * 0.08;
  vmin -= pad;
  vmax += pad;

  ctx.strokeStyle = "#1e2e44";
  ctx.lineWidth = 1;
  ctx.strokeRect(left, top, plotW, plotH);
  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  for (let i = 1; i < 4; i++) {
    const y = top + (plotH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + plotW, y);
    ctx.stroke();
  }

  ctx.fillStyle = "#9eafc5";
  ctx.font = "10px Consolas, monospace";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText(vmax.toFixed(2), left - 6, top + 4);
  ctx.fillText(((vmax + vmin) / 2).toFixed(2), left - 6, top + plotH / 2);
  ctx.fillText(vmin.toFixed(2), left - 6, top + plotH - 4);
  ctx.textAlign = "left";
  ctx.fillText("۰", left, rect.height - 4);
  ctx.textAlign = "right";
  ctx.fillText(String(s.n_steps - 1), left + plotW, rect.height - 4);
  ctx.textAlign = "center";
  ctx.font = "10px Tahoma";
  ctx.fillText("گام", left + plotW / 2, rect.height - 4);
  ctx.save();
  ctx.translate(10, top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.fillText("پتانسیل (واحد مدل)", 0, 0);
  ctx.restore();

  ctx.strokeStyle = voltageLayer === "hidden" ? "#66c6ff" : "#ffbe7b";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  vals.forEach((v, t) => {
    const x = left + (t / Math.max(1, vals.length - 1)) * plotW;
    const y = top + plotH - ((v - vmin) / (vmax - vmin)) * plotH;
    if (t === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  const curV = vals[currentStep] ?? vals[0] as number;
  const curX = left + (currentStep / Math.max(1, vals.length - 1)) * plotW;
  const curY = top + plotH - ((curV - vmin) / (vmax - vmin)) * plotH;
  ctx.fillStyle = "#60dfca";
  ctx.beginPath();
  ctx.arc(curX, curY, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(96,223,202,0.35)";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(curX, top);
  ctx.lineTo(curX, top + plotH);
  ctx.stroke();
  ctx.setLineDash([]);

  byId("voltageSummary").textContent =
    `لایه ${voltageLayer === "hidden" ? "پنهان" : "خروجی"} · نورون ${String(idx)} — گام ${String(currentStep)} مقدار ${curV.toFixed(3)}؛ محور عمودی واحد مدل است، نه ولت فیزیکی.`;
}

function drawHeatmaps(d: SimResult): void {
  const mode = (selectOf("weightMode").value as string) || "final";
  const wIn = resolveWeights(d.input_weights, d.initial_input_weights, mode);
  const wOut = d.output_weights ?? [];
  drawHeatmap(canvasOf("wIn"), wIn);
  drawHeatmap(canvasOf("wOut"), wOut);
  updateWeightLegends(wIn, wOut, mode);
}

function resolveWeights(finalW: number[][] | undefined, initW: number[][] | undefined, mode: string): number[][] {
  if (!finalW || !initW) return finalW ?? [];
  if (mode === "initial") return initW;
  if (mode === "delta") {
    return finalW.map((row, i) => row.map((v, j) => v - (initW[i]?.[j] ?? 0)));
  }
  return finalW;
}

function drawHeatmap(canvas: HTMLCanvasElement, w: number[][]): void {
  const ctx = ensureHiDPI(canvas);
  if (!ctx) return;
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = "#0c1421";
  ctx.fillRect(0, 0, rect.width, rect.height);
  if (w.length === 0 || !w[0] || w[0].length === 0) {
    ctx.fillStyle = "#9eafc5";
    ctx.font = "12px Tahoma";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("بدون داده", rect.width / 2, rect.height / 2);
    return;
  }
  const rows = w.length, cols = w[0].length;
  const flat = w.flat();
  let mn = Math.min(...flat), mx = Math.max(...flat);
  if (!Number.isFinite(mn) || !Number.isFinite(mx)) return;
  if (mx - mn < 1e-9) {
    mn -= 0.5;
    mx += 0.5;
  }
  const absMax = Math.max(Math.abs(mn), Math.abs(mx));
  const left = 28, right = 8, top = 18, bottom = 22;
  const plotW = rect.width - left - right;
  const plotH = rect.height - top - bottom;
  const cw = plotW / cols, ch = plotH / rows;

  ctx.strokeStyle = "#1e2e44";
  ctx.lineWidth = 1;
  ctx.strokeRect(left, top, plotW, plotH);

  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      const v = w[i]?.[j] ?? 0;
      const t = (v + absMax) / (2 * absMax);
      const hue = 215 - t * 40;
      const light = 18 + t * 52;
      const sat = 78;
      ctx.fillStyle = `hsl(${String(hue)}, ${String(sat)}%, ${String(light)}%)`;
      ctx.fillRect(left + j * cw + 0.5, top + i * ch + 0.5, cw - 1, ch - 1);
    }
  }

  ctx.fillStyle = "#9eafc5";
  ctx.font = "10px Consolas, monospace";
  ctx.textAlign = "center";
  for (let j = 0; j < cols; j++) {
    ctx.fillText(String(j), left + j * cw + cw / 2, top - 6);
  }
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i < rows; i++) {
    ctx.fillText(String(i), left - 6, top + i * ch + ch / 2);
  }
}

function updateWeightLegends(wIn: number[][], wOut: number[][], mode: string): void {
  const label = mode === "initial" ? "ابتدایی" : mode === "delta" ? "Δ نسبت به ابتدا" : "نهایی";
  const flatIn = wIn.flat();
  const flatOut = wOut.flat();
  const fmt = (arr: number[]): string => {
    if (arr.length === 0) return "بدون داده";
    const mn = Math.min(...arr).toFixed(3);
    const mx = Math.max(...arr).toFixed(3);
    return `${label} · کمینه ${mn} · بیشینه ${mx}`;
  };
  byId("wInLegend").textContent = fmt(flatIn);
  byId("wOutLegend").textContent = fmt(flatOut);
}

function updateInspection(): void {
  const host = byId("inspection");
  if (!lastResult || !lastResult.settings) {
    host.innerHTML = "<div><dt>وضعیت</dt><dd>هنوز داده‌ای ثبت نشده است.</dd></div>";
    return;
  }
  const d = lastResult;
  const s = d.settings as SimSettings;
  const step = currentStep;
  const layer = selectedLayer;
  const idx = selectedNeuron;
  const inpSpikes = d.input_spikes?.[step] ?? [];
  const hidSpikes = d.hidden_spikes?.[step] ?? [];
  const outSpikes = d.output_spikes?.[step] ?? [];
  const hidV = d.hidden_voltage?.[step] ?? [];
  const outV = d.output_voltage?.[step] ?? [];
  const spike = layer === "input" ? (inpSpikes[idx] ?? 0) : layer === "hidden" ? (hidSpikes[idx] ?? 0) : (outSpikes[idx] ?? 0);
  const volt = layer === "hidden" ? hidV[idx] : layer === "output" ? outV[idx] : undefined;
  const counts =
    layer === "input"
      ? (d.input_counts?.[idx] ?? 0)
      : layer === "hidden"
        ? (d.hidden_counts?.[idx] ?? 0)
        : (d.output_counts?.[idx] ?? 0);
  const rate = s.n_steps > 0 ? (counts / s.n_steps).toFixed(3) : "—";
  host.innerHTML = [
    `<div><dt>لایه / نورون</dt><dd>${layer} ${String(idx)}</dd></div>`,
    `<div><dt>گام جاری</dt><dd>${String(step)} / ${String(s.n_steps - 1)} · اسپایک: ${spike ? "۱" : "۰"}</dd></div>`,
    `<div><dt>کل اسپایک</dt><dd>${String(counts)} · نرخ ${rate}</dd></div>`,
    `<div><dt>پتانسیل</dt><dd>${volt !== undefined ? volt.toFixed(3) : "— (ورودی کدگذاری نرخی است)"}</dd></div>`,
    `<div><dt>نکته</dt><dd>اسپایک‌ها و ولتاژها همان گام بازپخش را نشان می‌دهند؛ داده از بک‌اند Python و مستقل از اجرای قبلی است.</dd></div>`,
  ].join("");
}

function updateVoltageSummary(): void {
  if (!lastResult || !lastResult.settings) return;
  drawVoltage(lastResult);
}

function setPlaybackStep(step: number): void {
  if (!lastResult || !lastResult.settings) return;
  const max = lastResult.settings.n_steps - 1;
  currentStep = Math.max(0, Math.min(max, step));
  inputOf("stepSlider").value = String(currentStep);
  byId("stepLabel").textContent = `${String(currentStep)} / ${String(max)}`;
  drawTopology(lastResult, currentStep);
  drawRaster(lastResult);
  drawVoltage(lastResult);
  updateInspection();
}

function playPlayback(): void {
  if (!lastResult || playTimer !== null) return;
  const speedSel = selectOf("speed");
  const stepsPerSec = parseInt(speedSel.value, 10) || 15;
  const interval = Math.max(16, Math.round(1000 / stepsPerSec));
  const btn = byId("playBtn") as HTMLButtonElement;
  btn.textContent = "توقف";
  btn.setAttribute("aria-label", "توقف بازپخش");
  playTimer = window.setInterval(() => {
    if (!lastResult || !lastResult.settings) {
      stopPlayback();
      return;
    }
    let next = currentStep + 1;
    if (next >= lastResult.settings.n_steps) next = 0;
    setPlaybackStep(next);
  }, interval);
}

function stopPlayback(): void {
  if (playTimer !== null) {
    window.clearInterval(playTimer);
    playTimer = null;
  }
  const btn = byId("playBtn") as HTMLButtonElement;
  if (btn) {
    btn.textContent = "پخش";
    btn.setAttribute("aria-label", "پخش گام‌های ثبت‌شده");
  }
}

function togglePlayback(): void {
  if (playTimer !== null) stopPlayback();
  else playPlayback();
}

function reset(): void {
  stopPlayback();
  lastResult = null;
  currentStep = 0;
  selectedLayer = "hidden";
  selectedNeuron = 0;
  voltageLayer = "hidden";
  voltageNeuron = 0;
  (byId("exportBtn") as HTMLButtonElement).disabled = true;
  const slider = inputOf("stepSlider");
  slider.value = "0";
  slider.max = "0";
  slider.disabled = true;
  (byId("playBtn") as HTMLButtonElement).disabled = true;
  byId("stepLabel").textContent = "—";
  byId("networkSummary").textContent = "برای مشاهدهٔ شبکه، یک آزمایش اجرا کنید.";
  byId("modelBadge").textContent = "بدون داده";
  byId("rasterSummary").textContent = "بدون داده";
  byId("voltageSummary").textContent = "بدون داده";
  byId("wInLegend").textContent = "بدون داده";
  byId("wOutLegend").textContent = "بدون داده";
  const honesty = byId("honesty");
  if (honesty) {
    honesty.textContent = "";
    honesty.hidden = true;
  }
  byId("stats").innerHTML = "";
  byId("inspection").innerHTML = "<div><dt>وضعیت</dt><dd>هنوز داده‌ای ثبت نشده است.</dd></div>";
  for (const id of ["topology", "raster", "voltage", "wIn", "wOut"]) clearCanvas(canvasOf(id));
  (selectOf("inspectLayer") as HTMLSelectElement).disabled = true;
  (selectOf("inspectNeuron") as HTMLSelectElement).disabled = true;
  (selectOf("voltageLayer") as HTMLSelectElement).disabled = true;
  (selectOf("voltageNeuron") as HTMLSelectElement).disabled = true;
  (selectOf("weightMode") as HTMLSelectElement).disabled = true;
  setStatus("آمادهٔ نخستین آزمایش", "");
  setFormError("");
  cachedNodes = [];
  syncPatternHint();
}

function exportJson(): void {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "eci-simulation.json";
  a.click();
  window.setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function setupTabs(): void {
  const tabs = [byId("networkTab"), byId("analysisTab")] as HTMLButtonElement[];
  const panels: Record<string, HTMLElement> = {
    networkTab: byId("networkPanel"),
    analysisTab: byId("analysisPanel"),
  };
  function activate(id: string): void {
    for (const t of tabs) {
      const sel = t.id === id;
      t.setAttribute("aria-selected", sel ? "true" : "false");
      t.tabIndex = sel ? 0 : -1;
      const p = panels[t.id] as HTMLElement;
      p.hidden = !sel;
    }
    if (lastResult) {
      drawTopology(lastResult, currentStep);
      drawRaster(lastResult);
      drawVoltage(lastResult);
      drawHeatmaps(lastResult);
    }
  }
  tabs.forEach((t) => {
    t.addEventListener("click", () => activate(t.id));
    t.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        const idx = tabs.indexOf(t);
        const next = e.key === "ArrowRight" ? (idx + 1) % tabs.length : (idx - 1 + tabs.length) % tabs.length;
        const nt = tabs[next] as HTMLButtonElement;
        nt.focus();
        activate(nt.id);
      }
    });
  });
}

function syncPatternHint(): void {
  const nInput = num("nInput", 4, 1, 32);
  const hint = byId("patternHint");
  if (hint) hint.textContent = `${String(nInput)} مقدار متناهی با کامای انگلیسی (الگو باید با n_input برابر باشد). با تغییر تعداد ورودی، الگو را به‌روزرسانی کنید.`;
}

function autoFixPattern(): void {
  const nInput = num("nInput", 4, 1, 32);
  const patEl = inputOf("pattern");
  const raw = patEl.value.trim();
  if (!raw) return;
  const parts = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (parts.length === nInput) return;
  if (parts.length === 0) {
    patEl.value = Array.from({ length: nInput }, (_, i) => ((i + 1) / nInput).toFixed(2)).join(",");
    return;
  }
  if (parts.length < nInput) {
    const last = parts[parts.length - 1] as string;
    const pad = Array.from({ length: nInput - parts.length }, () => last);
    patEl.value = [...parts, ...pad].join(",");
  } else {
    patEl.value = parts.slice(0, nInput).join(",");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  byId("settingsForm").addEventListener("submit", (e) => void run(e));
  byId("resetBtn").addEventListener("click", reset);
  byId("exportBtn").addEventListener("click", exportJson);
  byId("playBtn").addEventListener("click", togglePlayback);
  inputOf("stepSlider").addEventListener("input", (e) => {
    const v = parseInt((e.target as HTMLInputElement).value, 10);
    setPlaybackStep(Number.isNaN(v) ? 0 : v);
  });
  selectOf("speed").addEventListener("change", () => {
    if (playTimer !== null) {
      stopPlayback();
      playPlayback();
    }
  });
  selectOf("inspectLayer").addEventListener("change", (e) => {
    selectedLayer = (e.target as HTMLSelectElement).value as LayerName;
    if (lastResult?.settings) {
      const s = lastResult.settings;
      const max =
        selectedLayer === "input" ? s.n_input : selectedLayer === "hidden" ? s.n_hidden : s.n_output;
      selectedNeuron = Math.min(selectedNeuron, max - 1);
      rebuildNeuronOptions(selectOf("inspectNeuron"), selectedLayer, s);
      selectOf("inspectNeuron").value = String(selectedNeuron);
      if (lastResult) drawTopology(lastResult, currentStep);
      updateInspection();
    }
  });
  selectOf("inspectNeuron").addEventListener("change", (e) => {
    selectedNeuron = parseInt((e.target as HTMLSelectElement).value, 10) || 0;
    if (lastResult) drawTopology(lastResult, currentStep);
    updateInspection();
  });
  selectOf("voltageLayer").addEventListener("change", (e) => {
    voltageLayer = (e.target as HTMLSelectElement).value as "hidden" | "output";
    if (lastResult?.settings) {
      rebuildNeuronOptions(selectOf("voltageNeuron"), voltageLayer === "hidden" ? "hidden" : "output", lastResult.settings);
      voltageNeuron = 0;
      selectOf("voltageNeuron").value = "0";
      drawVoltage(lastResult);
    }
  });
  selectOf("voltageNeuron").addEventListener("change", (e) => {
    voltageNeuron = parseInt((e.target as HTMLSelectElement).value, 10) || 0;
    if (lastResult) drawVoltage(lastResult);
  });
  selectOf("weightMode").addEventListener("change", () => {
    if (lastResult) drawHeatmaps(lastResult);
  });
  inputOf("nInput").addEventListener("change", () => {
    syncPatternHint();
    autoFixPattern();
  });
  inputOf("nInput").addEventListener("input", syncPatternHint);
  canvasOf("topology").addEventListener("click", (e) => {
    const rect = canvasOf("topology").getBoundingClientRect();
    const hit = hitNode(e.clientX - rect.left, e.clientY - rect.top);
    if (hit) {
      selectedLayer = hit.layer;
      selectedNeuron = hit.idx;
      selectOf("inspectLayer").value = selectedLayer;
      if (lastResult?.settings) {
        rebuildNeuronOptions(selectOf("inspectNeuron"), selectedLayer, lastResult.settings);
        selectOf("inspectNeuron").value = String(selectedNeuron);
      }
      if (lastResult) drawTopology(lastResult, currentStep);
      updateInspection();
    }
  });
  window.addEventListener("resize", () => {
    if (lastResult) drawAll(lastResult);
  });
  document.addEventListener("keydown", (e) => {
    if (!lastResult || playTimer !== null) return;
    if (e.key === "ArrowRight") {
      e.preventDefault();
      setPlaybackStep(currentStep + 1);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      setPlaybackStep(currentStep - 1);
    } else if (e.key === " ") {
      const ae = document.activeElement as HTMLElement | null;
      if (ae && (ae.tagName === "INPUT" || ae.tagName === "SELECT" || ae.tagName === "BUTTON")) return;
      e.preventDefault();
      togglePlayback();
    }
  });
  setupTabs();
  syncPatternHint();
  void refreshStatus();
  for (const id of ["topology", "raster", "voltage", "wIn", "wOut"]) clearCanvas(canvasOf(id));
});
