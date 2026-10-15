/// <reference types="vite/client" />

declare module '@tabler/icons-react/dist/esm/icons/*.mjs' {
  import type { ForwardRefExoticComponent, RefAttributes, SVGProps } from 'react'
  const icon: ForwardRefExoticComponent<SVGProps<SVGSVGElement> & { size?: string | number; stroke?: string | number } & RefAttributes<SVGSVGElement>>
  export default icon
}
