# Initialize a package.json if you haven't already
    npm init -y

# Install tsx as a dev dependency
    npm install -D tsx


# Execute the script from your root directory using npx tsx:

assuming we are in `scripts/nwb_ts/`

    npx tsx example.ts

# Install h5wasm

    npm install h5wasm


# init vue 3 + vite 

# 1. Install Vue 3 and Plotly
    npm install vue plotly.js-dist-min h5wasm

# 2. Install Tailwind CSS and its peer dependencies for styling
    npm install -D tailwindcss postcss autoprefixer

# 3. Initialize Tailwind CSS configuration files
    npx tailwindcss init -p