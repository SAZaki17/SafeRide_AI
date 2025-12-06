<template>
  <v-container class="map-page pa-4">
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="origin"
          :disabled="loading"
          label="Origin Address"
          prepend-icon="mdi-flag-checkered"
          required
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-text-field
          v-model="destination"
          :disabled="loading"
          label="Destination Address"
          prepend-icon="mdi-map-marker-path"
          required
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-text-field
          v-model="departureTime"
          :disabled="loading"
          label="Departure Time (ISO 8601, optional)"
          placeholder="e.g., 2025-12-07T14:00:00+08:00"
          prepend-icon="mdi-clock-time-four-outline"
        />
      </v-col>

      <v-col cols="12">
        <v-btn
          block
          color="primary"
          :disabled="!origin || !destination || loading"
          large
          :loading="loading"
          @click="fetchAndDrawRoute"
        >
          <v-icon left>mdi-ray-start</v-icon>
          Get Safe Route & Weather
        </v-btn>
      </v-col>
    </v-row>

    <v-alert
      v-if="error"
      class="mb-4"
      dismissible
      type="error"
    >
      {{ error }}
    </v-alert>

    <v-card class="elevation-4 map-card">
      <div id="map" ref="map" />
    </v-card>

  </v-container>
</template>

<script>
  import { Loader } from '@googlemaps/js-api-loader'
  import axios from 'axios'

  export default {
    name: 'RouteMap',
    data () {
      return {
        // Input state
        origin: 'Subang Jaya, Malaysia', // Default for easy testing
        destination: 'Kuala Lumpur City Centre, Malaysia', // Default for easy testing
        departureTime: '', // Leave blank to use current time

        // Map state
        map: null,
        polyline: null,
        loader: null,

        // UI state
        loading: false,
        error: null,
      }
    },
    mounted () {
      // Initialize the Google Maps Loader once when the component is mounted
      this.loader = new Loader({
        // Loads key from the .env.local file
        apiKey: import.meta.env.VITE_GOOGLE_MAPS_KEY,
        version: 'weekly',
        libraries: ['geometry'],
      })

      // Initialize the map without loading a route
      this.initializeMap()
    },
    methods: {
      async initializeMap() {
        try {
          if (!import.meta.env.VITE_GOOGLE_MAPS_KEY) {
            this.error = 'Google Maps API key not configured. Please add VITE_GOOGLE_MAPS_KEY to .env.local'
            return
          }
          
          const google = await this.loader.load()
          
          if (!this.map) {
            const mapOptions = {
              center: { lat: 3.1390, lng: 101.6869 }, // Kuala Lumpur center
              zoom: 11,
            }
            this.map = new google.maps.Map(this.$refs.map, mapOptions)
          }
        } catch (error) {
          this.error = `Failed to load Google Maps: ${error.message}. Please check your API key.`
          console.error('Google Maps Error:', error)
        }
      },
      
      async fetchAndDrawRoute () {
        this.loading = true
        this.error = null

        try {
          if (!this.origin || !this.destination) {
            throw new Error('Please enter both Origin and Destination addresses.')
          }

          // 1. Fetch Route Data from your FastAPI Backend
          const API_URL = `${import.meta.env.VITE_API_BASE_URL}/route`
          const params = {
            origin: this.origin,
            destination: this.destination,
            // Only send departure_time if it's set
            departure_time: this.departureTime || undefined,
          }
          const response = await axios.get(API_URL, { params })

          const segments = response.data.segments
          if (segments.length === 0) {
            throw new Error('The backend could not calculate a route. Check address validity.')
          }

          // 2. Load Google Maps API (if not already loaded)
          const google = await this.loader.load()

          // 3. Initialize the Map (or reuse the existing one)
          if (!this.map) {
            const mapOptions = {
              center: { lat: segments[0].lat, lng: segments[0].lng },
              zoom: 12,
            }
            // The map renders into the ref="map" element
            this.map = new google.maps.Map(this.$refs.map, mapOptions)
          }

          // 4. Update or Create the Polyline
          const pathCoordinates = segments.map(s => ({ lat: s.lat, lng: s.lng }))

          if (this.polyline) {
            // Update existing polyline path
            this.polyline.setPath(pathCoordinates)
          } else {
            // Create new polyline
            this.polyline = new google.maps.Polyline({
              path: pathCoordinates,
              geodesic: true,
              strokeColor: '#00796B', // Teal color
              strokeOpacity: 1,
              strokeWeight: 6,
              map: this.map,
            })
          }

          // 5. Adjust the map view
          const bounds = new google.maps.LatLngBounds()
          for (const coord of pathCoordinates) bounds.extend(coord)
          this.map.fitBounds(bounds)

          console.log('Route displayed successfully!')
        } catch (error) {
          this.error = `Error: ${error.message}. See console for details.`
          if (error.response && error.response.data && error.response.data.detail) {
            this.error = `Backend Error: ${error.response.data.detail}`
          }
          console.error('Full Error:', error)
        } finally {
          this.loading = false
        }
      },
    },
  }
</script>

<style scoped>
.map-page {
  min-height: 100vh;
  background: #000;
  color: #fff;
}

.map-card {
  background: #000;
}

#map {
  width: 100%;
  height: 70vh;
  border-radius: 12px;
  overflow: hidden;
}
</style>
