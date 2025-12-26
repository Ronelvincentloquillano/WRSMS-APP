/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./wrsm_app/templates/**/*.html",
    "./wrsm_app/templates/*.html",
    "./static/src/**/*.{css,js}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}