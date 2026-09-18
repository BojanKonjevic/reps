let TIP: HTMLDivElement | null = null;

export function tipRow(color: string | null, text: string): HTMLDivElement {
  const row = document.createElement('div');
  row.className = 'tr';
  if (color) {
    const sw = document.createElement('span');
    sw.className = 'sw';
    sw.style.background = color;
    row.appendChild(sw);
  }
  row.appendChild(document.createTextNode(text));
  return row;
}

export function showTip(title: string, rows: Array<[string | null, string]>, x: number, y: number) {
  if (!TIP) {
    TIP = document.createElement('div');
    TIP.className = 'tip';
    TIP.style.display = 'none';
    document.body.appendChild(TIP);
  }
  const el = TIP;
  el.innerHTML = '';
  const tt = document.createElement('div');
  tt.className = 'tt';
  tt.textContent = title;
  el.appendChild(tt);
  rows.forEach(r => el.appendChild(tipRow(r[0], r[1])));
  el.style.display = 'block';
  const w = el.offsetWidth;
  el.style.left = (x + 18 + w > window.innerWidth ? x - w - 18 : x + 18) + 'px';
  el.style.top = y + 20 + 'px';
}

export function hideTip() {
  if (TIP) TIP.style.display = 'none';
}
