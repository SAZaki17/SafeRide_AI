# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SafeRide_AI is a weather forecast application for journey planning with the following structure:
- **Frontend**: Vue 3 + TypeScript + Vuetify application in `safe-ride-fe/safe-ride-cursor-hackathon/`
- **Backend**: Python Flask/FastAPI service in `safe-ride-be/` with Google Maps integration

## Commands

### Frontend Development (safe-ride-fe/safe-ride-cursor-hackathon/)
```bash
cd safe-ride-fe/safe-ride-cursor-hackathon
npm run dev           # Start development server
npm run build         # Build for production
npm run type-check    # Run TypeScript type checking
npm run lint          # Run ESLint with auto-fix
npm run preview       # Preview production build
```

### Backend Development (safe-ride-be/)
```bash
cd safe-ride-be
python -m pip install -r requirements.txt  # Install dependencies
python main.py        # Start backend server
```

## Architecture

### Frontend Architecture
- **Framework**: Vue 3 with Composition API and TypeScript
- **UI Framework**: Vuetify 3 (Material Design components)
- **State Management**: Pinia stores in `src/stores/`
- **Routing**: Vue Router with file-based routing via unplugin-vue-router
- **Layout System**: Vue layouts in `src/layouts/` using vite-plugin-vue-layouts-next
- **Auto-imports**: Components and composables auto-imported via unplugin-vue-components and unplugin-auto-import
- **Maps Integration**: Google Maps JavaScript API via @googlemaps/js-api-loader in RouteMap component

### Backend Architecture
- **Maps Service**: Google Maps API integration for route planning (`services/maps_service.py`)
- **Places Service**: Google Places API for location search (`services/places_service.py`)

### Key Components
- **RouteMap.vue**: Main map component handling Google Maps integration
- **AppFooter.vue**: Application footer component
- **default.vue**: Main layout template

### TypeScript Configuration
- Separate configs for app (`tsconfig.app.json`) and node (`tsconfig.node.json`)
- Auto-generated type definitions for components (`components.d.ts`) and router (`typed-router.d.ts`)

### Development Notes
- Uses file-based routing - pages in `src/pages/` automatically become routes
- Vuetify theme configuration in `src/plugins/vuetify.ts`
- SCSS styles with Vuetify integration in `src/styles/settings.scss`
- PWA capabilities via vite-plugin-pwa configuration