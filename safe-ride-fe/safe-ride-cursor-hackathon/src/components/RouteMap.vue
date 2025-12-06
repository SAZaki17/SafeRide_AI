<template>
  <v-container>
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="origin"
          label="Origin Address"
          prepend-icon="mdi-flag-checkered"
          required
          :disabled="loading"
        ></v-text-field>
      </v-col>

      <v-col cols="12" md="4">
        <v-text-field
          v-model="destination"
          label="Destination Address"
          prepend-icon="mdi-map-marker-path"
          required
          :disabled="loading"
        ></v-text-field>
      </v-col>

      <v-col cols="12" md="4">
        <v-text-field
          v-model="departureTime"
          label="Departure Time (ISO 8601, optional)"
          prepend-icon="mdi-clock-time-four-outline"
          placeholder="e.g., 2025-12-07T14:00:00+08:00"
          :disabled="loading"
        ></v-text-field>
      </v-col>

      <v-col cols="12">
        <v-btn
          color="primary"
          @click="fetchAndDrawRoute"
          :loading="loading"
          :disabled="!origin || !destination || loading"
          block
          large
        >
          <v-icon left>mdi-ray-start</v-icon>
          Get Safe Route & Weather
        </v-btn>
      </v-col>
    </v-row>

    <v-alert v-if="error" type="error" dismissible class="mb-4">
      {{ error }}
    </v-alert>

    <v-card class="elevation-4">
      <div id="map" ref="map" style="width: 100%; height: 600px"></div>
    </v-card>
  </v-container>
</template>

<script>
import { Loader } from "@googlemaps/js-api-loader";
import axios from "axios";

export default {
  name: "RouteMap",
  data() {
    return {
      // Input state
      origin: "Subang Jaya, Malaysia",
      destination: "Kuala Lumpur City Centre, Malaysia",
      departureTime: "",

      // Map state
      map: null,
      polyline: null,
      markers: [], // Array to store all map marker objects
      loader: null,

      // UI state
      loading: false,
      error: null,
    };
  },
  mounted() {
    // Initialize the Google Maps Loader once
    this.loader = new Loader({
      apiKey: process.env.VUE_APP_GOOGLE_MAPS_KEY,
      version: "weekly",
      libraries: ["geometry"],
    });

    // Load a default route on page load
    this.fetchAndDrawRoute();
  },
  methods: {
    clearMarkers() {
      if (this.markers.length > 0) {
        this.markers.forEach((marker) => marker.setMap(null));
        this.markers = [];
      }
    },

    async fetchAndDrawRoute() {
      this.loading = true;
      this.error = null;

      // Clear old markers and polyline
      this.clearMarkers();
      if (this.polyline) {
        this.polyline.setMap(null);
        this.polyline = null;
      }

      try {
        if (!this.origin || !this.destination) {
          throw new Error(
            "Please enter both Origin and Destination addresses.",
          );
        }

        // 1. Fetch Route Data (Now includes weather)
        const API_URL = `${process.env.VUE_APP_API_BASE_URL}/route`;
        const params = {
          origin: this.origin,
          destination: this.destination,
          departure_time: this.departureTime || undefined,
        };
        const response = await axios.get(API_URL, { params });

        const segments = response.data.segments;
        if (segments.length === 0) {
          throw new Error(
            "The backend could not calculate a route. Check address validity.",
          );
        }

        const google = await this.loader.load();

        // 2. Initialize or Reuse Map
        if (!this.map) {
          const mapOptions = {
            center: { lat: segments[0].lat, lng: segments[0].lng },
            zoom: 12,
          };
          this.map = new google.maps.Map(this.$refs.map, mapOptions);
        }

        // 3. Draw Polyline
        const pathCoordinates = segments.map((s) => ({
          lat: s.lat,
          lng: s.lng,
        }));

        if (this.polyline) {
          this.polyline.setPath(pathCoordinates);
        } else {
          this.polyline = new google.maps.Polyline({
            path: pathCoordinates,
            geodesic: true,
            strokeColor: "#00796B",
            strokeOpacity: 1.0,
            strokeWeight: 6,
            map: this.map,
          });
        }

        // 4. Draw Markers for Segments
        segments.forEach((segment, index) => {
          if (index === segments.length - 1) return; // Skip last point

          const isStart = index === 0;

          // Determine the icon URL based on weather icon code (using OpenWeatherMap URLs)
          const iconUrl =
            segment.weather_icon !== "N/A"
              ? `https://openweathermap.org/img/wn/${segment.weather_icon}@2x.png`
              : "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"; // Default blue pin

          // Override icon for the Start point
          const finalIcon = isStart
            ? "http://maps.google.com/mapfiles/ms/icons/green-dot.png" // Green pin for start
            : iconUrl;

          const markerTitle = isStart
            ? `START: ${segment.human_readable_time}`
            : `${segment.weather_condition} @ ${segment.human_readable_time}`;

          const marker = new google.maps.Marker({
            position: { lat: segment.lat, lng: segment.lng },
            map: this.map,
            title: markerTitle,
            icon: {
              url: finalIcon,
              scaledSize: new google.maps.Size(40, 40),
            },
          });

          // Create a richer Info Window displaying ALL fetched data
          const infoWindowContent = `
                    <div style="font-family: Arial; padding: 5px;">
                        <h4 style="margin-top: 0; color: #00796B;">${isStart ? "Route Start" : "Segment Checkpoint"}</h4>
                        <p>📍 **Location:** ${segment.place_name}</p>
                        <p>🕒 **ETA:** ${segment.human_readable_time}</p>
                        <p>☁️ **Weather:** ${segment.weather_condition}</p>
                        <p>🌡️ **Temp:** ${segment.temperature.toFixed(1)} °C</p>
                    </div>
                `;

          const infoWindow = new google.maps.InfoWindow({
            content: infoWindowContent,
          });

          // Add listener to open info window on click
          marker.addListener("click", () => {
            infoWindow.open({
              anchor: marker,
              map: this.map,
            });
          });

          this.markers.push(marker);
        });

        // 5. Adjust Bounds
        const bounds = new google.maps.LatLngBounds();
        pathCoordinates.forEach((coord) => bounds.extend(coord));
        this.map.fitBounds(bounds);

        console.log("Route and Weather displayed successfully!");
      } catch (e) {
        this.error = `Error: ${e.message}. See console for details.`;
        if (e.response && e.response.data && e.response.data.detail) {
          this.error = `Backend Error: ${e.response.data.detail}`;
        }
        console.error("Full Error:", e);
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
#map {
  border-radius: 8px;
}
</style>
