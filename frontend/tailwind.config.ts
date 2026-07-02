import type { Config } from 'tailwindcss';

export default {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        background: '#FFFFFF',
        primary: '#D8653B',
        secondary: '#8685D8',
        dark: '#212145',
        darkSecondary: '#313157',
        surface: '#EFE7E5',
      },
      boxShadow: {
        soft: '0 20px 60px -20px rgba(33, 33, 69, 0.15)',
      },
    },
  },
  plugins: [],
} satisfies Config;
