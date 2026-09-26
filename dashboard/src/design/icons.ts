// SSOT owner: icons. Consumers: <Icon> for SVG, canvas via Path2D from the same path.

export const icons = {
  // Trophy: cup with side handles, stem, and base. 16x16 viewBox.
  trophy:
    'M4.5 1.5h7v4.2a3.5 3.5 0 0 1-7 0V1.5z' +
    'M4.5 3H2.2a.9.9 0 0 0-.9 1c0 1.9 1.4 3.1 3.2 3.3' +
    'M11.5 3h2.3a.9.9 0 0 1 .9 1c0 1.9-1.4 3.1-3.2 3.3' +
    'M8 9.2v2.1M6.2 13.4h3.6M5.4 14.8h5.2',
  // Home: roof, walls, door.
  home: 'M2.5 8 8 2.5 13.5 8M4.5 6.5v7h7v-7M7 13.5v-3h2v3',
  chevronLeft: 'M10 3 5 8l5 5',
  chevronRight: 'M6 3l5 5-5 5',
  // Overview: four quiet squares.
  overview: 'M2.5 2.5h5v5h-5zM8.5 2.5h5v5h-5zM2.5 8.5h5v5h-5zM8.5 8.5h5v5h-5z',
  // Movements: pulse line.
  activity: 'M1.5 8h3l2-5 3 10 2-5h2.5',
  // Muscles: stacked layers.
  layers: 'M8 2.5l5.5 2.8L8 8.1 2.5 5.3zM2.5 8.3L8 11l5.5-2.7M2.5 11.3L8 14l5.5-2.7',
  // Program: calendar outline.
  calendar: 'M3 3.5h10v10H3zM3 6.2h10M5.8 2v2.6M10.2 2v2.6',
  // History: clock.
  clock: 'M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM8 5v3.4l2.3 1.4',
} as const;

export type IconName = keyof typeof icons;

export function trophyPath(scale = 1): Path2D {
  // Canvas draws the trophy from the same path data via Path2D.
  void scale;
  return new Path2D(icons.trophy);
}
