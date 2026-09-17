let TIP: HTMLDivElement | null = null;

export function tipRow(color: string | null, text: string): HTMLDivElement {
  const row = document.createElement("div"); row.className = "tr";
  if (color) { const sw = document.createElement("span"); sw.className = "sw"; sw.style.background = color; row.appendChild(sw); }
  row.appendChild(document.createTextNode(text)); return row;
}

export function showTip(title: string, rows: Array<[string | null, string]>, x: number, y: number) {
  if (!TIP) { TIP = document.createElement("div"); TIP.className = "tip"; TIP.style.display = "none"; document.body.appendChild(TIP); }
  TIP.innerHTML = "";
  const tt = document.createElement("div"); tt.className = "tt"; tt.textContent = title; TIP.appendChild(tt);
  rows.forEach(r => TIP.appendChild(tipRow(r[0], r[1])));
  TIP.style.display = "block";
  const w = TIP.offsetWidth;
  TIP.style.left = (x + 18 + w > window.innerWidth ? x - w - 18 : x + 18) + "px";
  TIP.style.top = (y + 20) + "px";
}

export function hideTip() { if (TIP) TIP.style.display = "none"; }