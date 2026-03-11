export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          50: '#f0f0f7',
          100: '#e0e0ee',
          200: '#c0c0dd',
          300: '#9090bb',
          400: '#6060aa',
          500: '#3d3d99',
          600: '#2d2d77',
          700: '#1e1e55',
          800: '#111133',
          900: '#080822',
        },
        coral: {
          400: '#ff7055',
          500: '#ff5533',
          600: '#e63d1a',
        }
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'serif'],
        body: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      }
    }
  }
}
