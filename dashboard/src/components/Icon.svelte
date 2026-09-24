<script lang="ts">
  // SSOT owner: icon rendering. Consumers: every page (replaces pasted SVGs).
  import { icons, type IconName } from '../design/icons';

  interface Props {
    name: IconName;
    size?: number;
    label?: string;
  }

  let { name, size = 22, label }: Props = $props();
</script>

<svg
  viewBox="0 0 16 16"
  width={size}
  height={size}
  role={label ? 'img' : undefined}
  aria-label={label}
  aria-hidden={label ? undefined : 'true'}
>
  <path
    d={icons[name]}
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
