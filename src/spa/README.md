# Flask Nova SPA

SPA (Single Page Application) support for the Flask Nova framework. This package provides esbuild integration for compiling and serving React/JSX components in Flask applications.

## Features

- **esbuild Integration**: Fast compilation of JSX/TSX files using esbuild
- **Automatic Binary Management**: Downloads and manages esbuild binaries for your platform
- **Hot Reload**: Automatic recompilation on file changes during development
- **Caching**: Intelligent caching based on file modification times
- **Flask Integration**: Seamless integration with Flask Nova's rendering system
- **React Support**: Built-in support for React with import maps

## Installation

Install as an optional extra:

```bash
pip install flask-nova[spa]
```


## Quick Start

```python
from flask_nova import FlaskNova
from spa import render_spa_template

app = FlaskNova(__name__)

@app.route('/')
def index():
    html = render_spa_template(
        'src/App.jsx',
        context={'user': 'John', 'items': [1, 2, 3]},
        template_vars={'title': 'My App'}
    )
    return html
```

`render_spa_template` is the intended route helper. It uses `NovaEngine` internally to compile your source file, and it can be configured with a custom `EsbuildWrapper` when needed.

## React entry helper

For SPA entry points, create a small helper function like `Main` that mounts your component and accepts props.

Example `script.js`:

```js
function Main(App, React, ReactDOM, props = {}) {
  const rootElement = document.getElementById("root");
  if (!rootElement) {
    console.error("Root element not found!");
    return;
  }

  const root = ReactDOM.createRoot(rootElement);
  root.render(React.createElement(App, props));
}

export default Main;
```

Then your `App.jsx` should use global browser imports from `window` and pass state through the helper:

```jsx
const React = window.React;
const ReactDOM = window.ReactDOM;
import Main from "./script";

const initialState = window.NOVA_STATE || {};

function App({ state = initialState }) {
  return (
    <div>
      <h1>Flask Nova SPA Example</h1>
      <p>Hello, {state.user}</p>
    </div>
  );
}

Main(App, React, ReactDOM, { state: initialState });
```

This pattern is used in `src/spa_ex/app.py` and ensures your JSX entrypoint is mounted correctly in the browser.

## Hot Reload

### Automatic Hot Reload (Recommended)

For automatic hot-reloading during development, use the `SpaHotReloadExtension`:

```python
from flask_nova import FlaskNova
from spa import render_spa_template, SpaHotReloadExtension

app = FlaskNova(__name__)
app.debug = True  # Enable debug mode

# Automatic hot-reload when app starts in debug mode
spa_ext = SpaHotReloadExtension(app, paths="src", output_dir=".dist")

@app.route('/')
def index():
    return render_spa_template('src/App.jsx', {'user': 'John'})
```

The extension automatically starts watching for file changes when the Flask app is in debug mode. You can configure it via app config:

```python
app.config['SPA_HOT_RELOAD_PATHS'] = ['src', 'components']
app.config['SPA_HOT_RELOAD_OUTPUT_DIR'] = '.build'
app.config['SPA_HOT_RELOAD_INTERVAL'] = 0.5
app.config['SPA_HOT_RELOAD_AUTO_START'] = True  # Default: True in debug mode
```

### Manual Hot Reload

Alternatively, manually start the watcher:

```python
from flask_nova import FlaskNova
from spa import render_spa_template, watch_spa

app = FlaskNova(__name__)

# Manual start
watcher = watch_spa("src", output_dir=".dist", interval=0.5)

@app.route('/')
def index():
    return render_spa_template('src/App.jsx', {'user': 'John'})
```

The watcher will detect changes to `.jsx`, `.tsx`, `.js`, and `.ts` files under the watched path and recompile them automatically.

## API Reference

### EsbuildWrapper

Main compiler class for bundling JavaScript/TypeScript/React code.

```python
compiler = EsbuildWrapper(
    esbuild_path="./bin/esbuild.exe",  # Path to esbuild binary
    bundle=True,                       # Enable bundling
    format="iife",                     # Output format
    platform_target="browser",         # Target platform
    minify=False,                      # Enable minification
    source_map=True,                   # Generate source maps
    loaders={'.png': 'file'},          # Custom loaders
)
```

### NovaEngine

Main rendering engine with caching support.

```python
# Compile and cache a file
compiled_file = await NovaEngine.compile_file('src/App.jsx')

# Render with context
html = await NovaEngine.render(
    'src/App.jsx',
    context={'data': 'value'},
    template_vars={'title': 'App Title'}
)
```

### SpaHotReloadExtension

Flask-Nova extension for automatic SPA hot-reloading during development.

```python
# Initialize with app
spa_ext = SpaHotReloadExtension(app, paths="src", output_dir=".dist")

# Manual control
spa_ext.start_watching()
spa_ext.stop_watching()
```

### SpaHotReloader

Low-level file watcher class used by `watch_spa` and `SpaHotReloadExtension`.

```python
watcher = SpaHotReloader(paths="src", output_dir=".dist", interval=1.0)
watcher.start()
# ... do work ...
watcher.stop()
```

### Utility Functions

```python
# Download esbuild binary
binary_path = get_esbuild_binary(version="0.27.4", target_dir="./bin")

# Route helper
html = render_spa_template('src/App.jsx', {'context': 'data'})

# Advanced configuration
from spa import EsbuildWrapper
compiler = EsbuildWrapper(esbuild_path=binary_path, minify=True)
html = render_spa_template(
    'src/App.jsx',
    {'context': 'data'},
    compiler=compiler
)
```

## Configuration

### Esbuild Options

The `EsbuildWrapper` supports many esbuild options:

- `bundle`: Enable/disable bundling
- `format`: Output format (`iife`, `cjs`, `esm`)
- `platform_target`: Target platform (`browser`, `node`)
- `target`: JavaScript target version (`es6`, `es2015`, etc.)
- `tree_shaking`: Enable tree shaking
- `source_map`: Generate source maps
- `minify`: Minify output
- `loaders`: Custom file loaders

### SpaHotReloadExtension Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `SPA_HOT_RELOAD_PATHS` | `str` or `list[str]` | `["src", "spa", "frontend", "client"]` | Paths to watch for file changes |
| `SPA_HOT_RELOAD_OUTPUT_DIR` | `str` | `".dist"` | Directory to output compiled files |
| `SPA_HOT_RELOAD_INTERVAL` | `float` | `1.0` | Seconds between file system checks |
| `SPA_HOT_RELOAD_AUTO_START` | `bool` | `True` | Auto-start watcher in debug mode |

### Import Maps

The generated HTML includes an import map for React:

```html
<script type="importmap">
{
  "imports": {
    "react": "https://esm.sh/react@18",
    "react-dom": "https://esm.sh/react-dom@18"
  }
}
</script>
```
