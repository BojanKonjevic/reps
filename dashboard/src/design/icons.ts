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
} as const;

export type IconName = keyof typeof icons;

export function trophyPath(scale = 1): Path2D {
  // Canvas draws the trophy from the same path data via Path2D.
  void scale;
  return new Path2D(icons.trophy);
}
