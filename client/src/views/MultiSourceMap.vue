<template>
  <div class="page-container" :class="{ 'is-global-loading': isUploading || isFetching || isRefreshing }">
    
    <div v-if="isMapReady" class="map-wrapper" 
     :class="{ 
        'show-glacier-names': currentRegion === 'Antarctica' && zoom >= 6,
        'show-basin-names': (currentRegion === 'Antarctica' && zoom >= 1) || (currentRegion === 'Greenland' && zoom >= 3)
     }" 
     :style="{ height: mapHeightPercent + '%' }">
	 
	 <div v-if="isMapBusy" class="map-interaction-blocker"></div>
	 
      <l-map 
	    :key="currentRegion"
        ref="map" 
        v-model:zoom="zoom" 
        v-model:center="center" 
		:style="{ pointerEvents: isMapBusy ? 'none' : 'auto' }"
        :use-global-leaflet="false" 
		:options="mapOptions"
        @click="onMapClick"
		@mousemove="onMapMouseMove"  @mouseup="onMapMouseUp"
		@moveend="syncUrl"
      >		
		<l-control-scale position="bottomleft" :imperial="false" :metric="true"></l-control-scale>
		
        <l-wms-tile-layer 
          :url="wmsBaseUrl"
          layers="BlueMarble_ShadedRelief_Bathymetry"
          format="image/jpeg"
          :transparent="false"
          name="NASA Blue Marble"
          attribution="NASA GIBS"
          :options="{ crossOrigin: 'anonymous' }"
        ></l-wms-tile-layer>
		
		<l-wms-tile-layer 
		  :url="wmsLandsatUrl" 
		  layers="landsat_mosaic" 
		  format="image/png" 
		  :transparent="true" 
		  :opacity="1.0" 
		  :z-index="5" 
		  name="Landsat Mosaic" 
		  :visible="selectedBasemap === 'satellite'"
		  :options="{ crossOrigin: 'anonymous', minZoom: 4 }"
		></l-wms-tile-layer>

		<div class="map-title-overlay">
		  <h1 class="shiver-title">SHIVER</h1>
		  <div class="shiver-subtitle">Timeseries Explorer</div>
		</div>
		
		<transition name="fade">
		  <div 
			  v-if="showFeedbackPopup" 
			  class="feedback-popup"
			  @click.stop
			  @mousedown.stop
			  @dblclick.stop
		  >
          <div class="feedback-content">
             Enjoying SHIVER? Please complete 
			 <AppLink to="https://docs.google.com/forms/d/e/1FAIpQLSfsFX-w19UXjlVDpY7PeQlo0_482tHYPTVuatWup-B3OdZOrA/viewform?usp=publish-editor" target="_blank" rel="noopener" class="text-link">this short form</AppLink>
             to provide feedback.
          </div>
          
          <button class="feedback-close" @click="closeFeedbackPopup">
            &times;
          </button>
        </div>
      </transition>
	  
		<Transition name="fade">
			  <div v-if="statusMessage" class="status-toast">
				<div class="status-content">
				  <span class="message-display-spinner" v-if="isMessageSpinnerRequired"></span>
				  {{ statusMessage }}
				</div>
			  </div>
		</Transition>
		
		<l-wms-tile-layer
		  :url="wmsOverlayUrl"
		  layers="hillshade"
		  format="image/png"
		  :transparent="true"
		  :opacity="1.0"
		  :z-index="10" 
		  name="Topography"
		  :visible="selectedBasemap === 'hillshade'"
		  :options="{ crossOrigin: 'anonymous' }"
		></l-wms-tile-layer>
		
		<l-wms-tile-layer
		   v-if="wmsOverlayUrl"
		   :visible="activeMode === 'overview' && overlayLayer === 'speed'"
		  :url="wmsOverlayUrl"
		  layers="default_speed"
		  format="image/png"
		  :transparent="true"
		  :opacity="0.8"
		  :z-index="30" 
		  name="Ice Speed"
		  :options="{ crossOrigin: 'anonymous' }"
		></l-wms-tile-layer>
		
		<l-wms-tile-layer
		  v-if="wmsOverlayUrl"
		  :visible="activeMode === 'overview' && overlayLayer === 'count'"
		  :url="wmsOverlayUrl"
		  layers="count"
		  format="image/png"
		  :transparent="true"
		  :opacity="0.5"
		  :z-index="30" 
		  name="Measurement Count"
		  :options="{ crossOrigin: 'anonymous' }"
		></l-wms-tile-layer>
		
		<l-wms-tile-layer
		  v-if="wmsOverlayUrl"
		  :visible="activeMode === 'overview' && overlayLayer === 'trend'"
		  :url="wmsOverlayUrl"
		  layers="trend"
		  format="image/png"
		  :transparent="true"
		  :opacity="0.5"
		  :z-index="30" 
		  name="Speed Trend"
		  :options="{ crossOrigin: 'anonymous' }"
		></l-wms-tile-layer>
		
		<l-wms-tile-layer
		   v-if="wmsOverlayUrl"
		  :visible="activeMode === 'overview' && overlayLayer === 'range'"
		  :url="wmsOverlayUrl"
		  layers="range"
		  format="image/png"
		  :transparent="true"
		  :opacity="0.5"
		  :z-index="30" 
		  name="Measurement Range"
		  :options="{ crossOrigin: 'anonymous' }"
		></l-wms-tile-layer>
		
		<l-wms-tile-layer
		  v-if="wmsVectorUrl"
		  :visible="activeMode === 'overview' && isFlowActive"
		  :url="wmsVectorUrl"
		  layers="vectors"
		  format="image/png"
		  :transparent="true"
		  name="Flow direction arrows"
		  :z-index="50"
		  :options="{ crossOrigin: 'anonymous' }"
		></l-wms-tile-layer>
		
		<l-wms-tile-layer
		  v-if="analysisWmsUrl"
		  :key="analysisWmsUrl" 
		  :url="analysisWmsUrl"
		  :visible="activeMode === 'analysis'"
		  layers="analysis_layer"
		  format="image/png"
		  :transparent="true"
		  :opacity="0.7"
		  :z-index="100"
		  @loading="onAnalysisLoading"
		  @load="onAnalysisComplete"
		  @tileerror="onAnalysisError"
		></l-wms-tile-layer>
		
        <l-geo-json 
		  v-if="currentBasinData" 
		  :geojson="currentBasinData"
		  :options="basinOptions"
		  :options-style="outlineStyle"
		  :z-index="500"
		></l-geo-json>
		
		<l-geo-json 
          v-if="glacierNamesData && currentRegion === 'Antarctica'" 
          :geojson="glacierNamesData"
          :options="glacierLabelOptions"
        ></l-geo-json>
				
        <template v-for="(point, index) in selectedPoints" :key="point.id">
			<l-rectangle
			   :bounds="getSquareBounds( point.lat, point.lon, point.buffer !== undefined ? point.buffer : pendingBuffer.value )"
			   :color="point.color"
			   :fill-color="point.color"
			   :fill-opacity="0.3"
			   :weight="1"
			   :interactive="true" 
			   class-name="draggable-feature"
			   @mousedown="startPointDrag($event, index)"
			   @click="stopPropagation"  
			/>
			<l-circle-marker 
			   :lat-lng="[point.lat, point.lon]"
			   :radius="3" 
			   :color="point.color"
			   :fill-color="point.color"
			   :fill-opacity="1.0" 
			   :weight="1"
			   class-name="draggable-feature"
			   @mousedown="startPointDrag($event, index)"
			   @click="stopPropagation"
			>
			   <l-tooltip>{{ getSiteLabel(point, index) }}</l-tooltip>
			</l-circle-marker>
		</template>
		
		<l-layer-group :visible="showMargins" :z-index="400">
			  <l-geo-json 
				v-if="iceEdgeData" 
				:geojson="iceEdgeData" 
				:options-style="() => iceEdgeStyle"
			  ></l-geo-json>

			  <l-geo-json 
				v-if="currentRegion === 'Antarctica' && groundingLineData" 
				:geojson="groundingLineData" 
				:options-style="() => groundingLineStyle"
			  ></l-geo-json>
		</l-layer-group>
		
      </l-map>
	  
      <div class="legend-container">

        <div class="legend-box" v-if="activeMode === 'overview' && (overlayLayer !== 'none' || isFlowActive || showMargins)">
        
			<div v-if="overlayLayer !== 'none'" class="scalar-legend-group">
				<div v-if="overlayLayer === 'speed'">
				  <h4>Ice Speed (Log Scale)</h4>
				  <div class="legend-bar speed-gradient"></div>
				  <div class="legend-bar-labels">
					<span>1</span>
					<span>3000</span>
				  </div>
				</div>

				<div v-else-if="overlayLayer === 'count'">
				  <h4>Measurement Count</h4>
				  <div class="legend-bar viridis-gradient"></div>
				  <div class="legend-bar-labels">
					<span>0</span>
					<span>{{ maxCountLabel }}</span>
				  </div>
				</div>
				
				<div v-else-if="overlayLayer === 'range'">
				  <h4>Measurement Range</h4>
				  <div class="legend-bar magma-gradient"></div>
				  <div class="legend-bar-labels">
					<span>0</span>
					<span>50</span>
				  </div>
				</div>
		
				<div v-else-if="overlayLayer === 'trend'">
				  <h4>Speed Trend (m/yr<sup>2</sup>)</h4>
				  <div class="legend-bar trend-gradient"></div>
				  <div class="legend-bar-labels">
					<span>{{ minTrendLabel }}</span>
					<span>0</span>
					<span>{{ maxTrendLabel }}</span>
				  </div>
				</div>
			</div>
			
			<div v-if="isFlowActive" class="vector-legend-group">
				<div v-if="overlayLayer !== 'none'" class="legend-separator"></div>				
				<div class="vector-row">
				  <svg :width="arrowPixelWidth + 15" height="24" class="vector-arrow-svg">
					 <defs>
					   <marker id="arrowhead" markerWidth="8" markerHeight="6" 
							   refX="7" refY="3" orient="auto">
						 <polygon points="0 0, 8 3, 0 6" fill="#333" />
					   </marker>
					 </defs>
					 
					 <line 
					   x1="0" y1="12" 
					   :x2="Math.max(arrowPixelWidth, 20) + 5" y2="12"
					   stroke="#333" 
					   stroke-width="2" 
					   marker-end="url(#arrowhead)" 
					 />
				  </svg>
				  <span class="vector-label">{{ vectorScaleLabel }}</span>
				</div>
			</div>
			
			<div v-if="showMargins" style="margin-top: 2px; border-top: 1px solid #ccc; padding-top: 2px;">			  
			  <div class="map-legend-item">
				<div class="map-legend-line" style="background: black;"></div>
				<span class="map-legend-label">Ice Margin</span>
			  </div>

			  <div class="map-legend-item" v-if="currentRegion === 'Antarctica'">
				<div class="map-legend-line" style="background: magenta;"></div>
				<span class="map-legend-label">Grounding Line</span>
			  </div>
			</div>
			
		</div>
		
		<div class="legend-box" v-if="activeMode === 'analysis'">
			<div class="scalar-legend-group">
			  
			  <div v-if="analysisVariable === 'speed' && !isDifferenceMode">
				<h4>Ice Speed (m/yr)</h4>
				<div class="legend-bar batlow-gradient"></div>
				<div class="legend-bar-labels">
				  <span>0</span>
				  <span>{{ colorVmax }}</span>
				</div>
			  </div>

			  <div v-else-if="analysisVariable === 'speed' && isDifferenceMode">
				<h4>Speed Difference (m/yr)</h4>
				<div class="legend-bar" :style="dynamicVikStyle"></div>
				<div class="legend-bar-labels-dynamic">
					<span class="label-min">{{ colorVmin }}</span>
					<span class="label-zero" v-if="colorVmin < 0 && colorVmax > 0" :style="{ left: zeroPivotPercentage + '%' }">0</span>
					<span class="label-max">{{ colorVmax }}</span>
				</div>
			  </div>

			  <div v-else-if="analysisVariable === 'count'">
				<h4>Measurement Count</h4>
				<div class="legend-bar viridis-gradient"></div>
				<div class="legend-bar-labels">
				  <span>0</span>
				  <span>{{ colorVmax }}</span>
				</div>
			  </div>

			  <div v-else-if="analysisVariable === 'trend'">
				<h4>Speed Trend (m/yr<sup>2</sup>)</h4>
				<div class="legend-bar" :style="dynamicVikStyle"></div>
				<div class="legend-bar-labels-dynamic">
					<span class="label-min">{{ colorVmin }}</span>
					<span class="label-zero" v-if="colorVmin < 0 && colorVmax > 0" :style="{ left: zeroPivotPercentage + '%' }">0</span>
					<span class="label-max">{{ colorVmax }}</span>
				</div>
			  </div>

			</div>
		</div>
		
	  </div>
	  
	  <div class="map-toolbar-left">
		<div class="toolbar-group-row">
			<button 
			  id="btn-switch-greenland" class="panel-btn" 
			  :class="{ 'active': currentRegion === 'Greenland' }"
			  @click="currentRegion = 'Greenland'; switchRegion()"
			  title="Switch to Greenland"
			>
			  <greenlandIcon class="btn-icon-svg" />
			</button>

			<button 
			  id="btn-switch-antarctica" class="panel-btn" 
			  :class="{ 'active': currentRegion === 'Antarctica' }"
			  @click="currentRegion = 'Antarctica'; switchRegion()"
			  title="Switch to Antarctica"
			>
			  <antarcticaIcon class="btn-icon-svg" />
			</button>
		</div>
	  </div>
	  
      <div class="map-toolbar">
	  
		  <div class="menu-trigger">
			<button class="panel-btn" title="Open Toolbox">
			  <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none">
				<line x1="3" y1="12" x2="21" y2="12"></line>
				<line x1="3" y1="6" x2="21" y2="6"></line>
				<line x1="3" y1="18" x2="21" y2="18"></line>
			  </svg>
			</button>
		  </div>
		  
		  <div class="tools-wrapper">

			  <div class="toolbar-group">
			    <button 
				  id="btn-overlays" class="panel-btn" 
				  @click="checkAuth(() => showLayerManager = !showLayerManager)"
				  :class="{ 'active': showLayerManager }" 
				  title="Map Layers & Analysis"
				>
				  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
					<polyline points="2 12 12 17 22 12"></polyline>
					<polyline points="2 17 12 22 22 17"></polyline>
				  </svg>
				</button>
                 
				<label 
				  id="btn-upload-file"  class="panel-btn" 
				  :class="{ 'active': isUploading }" 
				  title="Upload File (KML, KMZ, GeoJSON or zipped shapefile)"
				>
				  <input type="file" @change="handleFileUpload" accept=".zip,.geojson,.kml,.kmz" hidden :disabled="isUploading">
				  <span v-if="isUploading" class="spinner-small"></span>
				  <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
					<polyline points="17 8 12 3 7 8" />
					<line x1="12" y1="3" x2="12" y2="15" />
				  </svg>
				</label>

				<button 
				  id="btn-advanced" class="panel-btn" 
				  @click="checkAuth(() => showAdvanced = !showAdvanced)"
				  :class="{ 'active': showAdvanced }" 
				  title="Advanced Options"
				>
				  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
					<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84a.484.484 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.488.488 0 0 0-.59.22L2.09 8.83a.488.488 0 0 0 .12.61l2.03 1.58c-.05.3-.07.63-.07.94s.02.64.07.94l-2.03 1.58a.488.488 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.27.41.48.41h3.84c.24 0 .44-.17.48-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.488.488 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
				  </svg>
				</button>

				<button id="btn-help-trigger" class="panel-btn" @click="showHelp = true" title="Help">
				  <span><strong>?</strong></span>
				</button>
			  </div>

			  <div class="toolbar-group" v-if="selectedPoints.length > 0">
				<button id="btn-download-data" class="panel-btn" @click="checkAuth(handleDownload)" :class="{ 'active': isDownloading }" :disabled="isDownloading" :title="xlsxDownloadLabel">
				   <span v-if="isDownloading" class="spinner-small"></span>
				   <excelIcon v-else class="btn-icon-svg" />
				</button>

				<button id="btn-download-chart" class="panel-btn" @click="checkAuth(downloadChartImage)" :class="{ 'active': isDownloadingChart }" :disabled="isDownloadingChart" :title="chartDownloadLabel">
				   <span v-if="isDownloadingChart" class="spinner-small"></span>
				   <graphIcon v-else class="btn-icon-svg" />
				</button>

			  </div>

			</div>
			
		</div>
		
		
		<div v-if="showLayerManager" class="advanced-popup-container layer-popup-override">
			<div class="advanced-card">
			  
			  <div class="card-header">
				<strong>Map Layers & Analysis</strong>
				<div class="header-actions">
				  <button @click="showLayerManager = false" class="btn-close">&times;</button>
				</div>
			  </div>
			  
			  <div class="card-body custom-scrollbar">
				
				<div class="opt-group" style="margin-bottom: 25px;">
					<div class="custom-tabs">
					  <label class="tab-btn" :class="{ active: activeMode === 'overview' }">
						<input type="radio" value="overview" v-model="activeMode" hidden> 
						<span>Overview</span>
					  </label>
					  <div class="tab-divider"></div>
					  <label class="tab-btn" :class="{ active: activeMode === 'analysis' }">
						<input type="radio" value="analysis" v-model="activeMode" hidden> 
						<span>Analysis</span>
					  </label>
					</div>
				  </div>
				  
				  <hr class="divider">

				  <template v-if="activeMode === 'overview'">
					
					<div class="opt-group">
						<label class="group-label">Basemap</label>
						<div class="checkbox-grid">
						  <label class="checkbox-pill">
							<input type="radio" value="none" v-model="selectedBasemap"> 
							<span>None</span>
						  </label>
						  <label class="checkbox-pill" :class="{ 'is-disabled': currentRegion === 'Antarctica' }" @click.prevent="toggleBasemap('satellite')">
							<input type="radio" value="satellite" v-model="selectedBasemap"> 
							<span>Satellite</span>
						  </label>
						  <label class="checkbox-pill" @click.prevent="toggleBasemap('hillshade')">
							<input type="radio" value="hillshade" v-model="selectedBasemap"> 
							<span>Topography</span>
						  </label>
						</div>
					</div>
					
					<hr class="divider">

					<div class="opt-group">
						<label class="group-label">Overlays</label>
						<div class="checkbox-grid">
						  <label class="checkbox-pill">
							<input type="radio" value="none" v-model="overlayLayer"> 
							<span>None</span>
						  </label>
						  <label class="checkbox-pill" @click.prevent="toggleOverlay('speed')">
							<input type="radio" value="speed" v-model="overlayLayer"> 
							<span>Speed</span>
						  </label>
						  <label class="checkbox-pill" @click.prevent="toggleOverlay('trend')">
							<input type="radio" value="trend" v-model="overlayLayer"> 
							<span>Speed Trend</span>
						  </label>
						  <label class="checkbox-pill" @click.prevent="toggleOverlay('count')">
							<input type="radio" value="count" v-model="overlayLayer"> 
							<span>Measurement Count</span>
						  </label>
						  <label class="checkbox-pill" @click.prevent="toggleOverlay('range')">
							<input type="radio" value="range" v-model="overlayLayer"> 
							<span>Measurement Range</span>
						  </label>
						</div>
					</div>
					
					<hr class="divider">
					
					<div class="opt-group">
						<label class="group-label">Additional Layers</label>
						<div class="checkbox-grid">
						  <label class="checkbox-pill">
							<input type="checkbox" v-model="isFlowActive"> 
							<span>Flow Direction</span>
						  </label>
						  <label class="checkbox-pill">
							<input type="checkbox" v-model="showMargins"> 
							<span>Ice Margins</span>
						  </label>
						</div>
					</div>
					
					<hr class="divider">
					
					<div class="opt-group">
						<label class="group-label">Basin Outlines</label>
						<div class="checkbox-grid">
						  <label v-for="basin in availableBasins" :key="basin.id" class="checkbox-pill" @click.prevent="toggleBasin(basin.id)">
							<input type="radio" :checked="selectedBasinId === basin.id"> 
							<span>{{ basin.label }}</span>
						  </label>
						</div>
					</div>
					
				</template>

				<template v-if="activeMode === 'analysis'">
				  
				  <div class="opt-group">
					<label class="group-label">Variable</label>
					<div class="checkbox-grid">
					  <label class="checkbox-pill">
						<input type="radio" value="speed" v-model="analysisVariable"> 
						<span>Speed</span>
					  </label>
					  <label class="checkbox-pill">
						<input type="radio" value="trend" v-model="analysisVariable"> 
						<span>Speed Trend</span>
					  </label>
					  <label class="checkbox-pill">
						<input type="radio" value="count" v-model="analysisVariable"> 
						<span>Measurement Count</span>
					  </label>
					</div>
				  </div>
				  
				  <hr class="divider">
				  
				  <div class="opt-group">
					<label class="group-label">Data Source</label>
					<select class="modern-select" v-model="selectedSource">
					  <option value="" disabled>Select a source...</option>
					  <option v-for="source in analysisDropdownSources" :key="source" :value="source">
						{{ formatSourceName(source) }}
					  </option>
					</select>
				  </div>

				  <div class="opt-group" v-if="analysisVariable === 'speed'">
					<label class="group-label">Measurement Epoch</label>
					<select class="modern-select" v-model="selectedEpoch">
					  <option value="" disabled>Select a date range...</option>
					  <option value="average">{{ longTermAverageLabel }}</option>
					  <option v-for="epoch in filteredEpochs" :key="epoch.index" :value="epoch.index">
						{{ formatEpochDates(epoch) }}
					  </option>
					</select>
				  </div>

				  <div v-if="analysisVariable === 'speed'">
					<hr class="divider">
					<div class="opt-group">
					  <div class="checkbox-grid">
						<label class="checkbox-pill">
						  <input type="checkbox" v-model="isDifferenceMode"> 
						  <span>Calculate speed change?</span>
						</label>
					  </div>
					  
					  <div v-if="isDifferenceMode" style="margin-top: 10px;">
						<label class="group-label">Reference Data Source</label>
						<select class="modern-select" v-model="compareSource">
						  <option value="" disabled>Select baseline source...</option>
						  <option v-for="source in analysisDropdownSources" :key="'comp-src-'+source" :value="source">
							{{ formatSourceName(source) }}
						  </option>
						</select>
					  </div>

					  <div v-if="isDifferenceMode && compareSource" style="margin-top: 10px;">
						  <label class="group-label">Reference epoch</label>
						  <select class="modern-select" v-model="compareEpoch">
							<option value="" disabled>Select baseline epoch...</option>
							<option value="average">{{ longTermAverageLabelCompare }}</option>
							<option v-for="epoch in filteredCompareEpochs" :key="'comp-ep-'+epoch.index" :value="epoch.index">
							  {{ formatEpochDates(epoch) }}
							</option>
						  </select>
					   </div>
					</div>
				  </div>

				  <hr class="divider">

				  <div class="opt-group" v-if="analysisVariable === 'speed' && !isDifferenceMode">
					  <label class="group-label">Colour Scale Limit (m/yr)</label>
					  <div class="param-item">
						<div class="param-info">
						  <span>Max Speed</span>
						  <input type="number" v-model.number="colorVmax" class="param-val-input">
						</div>
						<input type="range" v-model.number="colorVmax" min="100" max="10000" step="100" class="modern-slider">
					  </div>
					</div>

					<div class="opt-group" v-else-if="analysisVariable === 'speed' && isDifferenceMode">
					  <label class="group-label">Colour Scale Limit (m/yr)</label>
					  <div class="param-item">
						<div class="param-info">
						  <span>Min</span>
						  <input type="number" v-model.number="colorVmin" class="param-val-input">
						</div>
						<input type="range" v-model.number="colorVmin" min="-3000" max="3000" step="100" class="modern-slider">
					  </div>
					  <div class="param-item" style="margin-top: 10px;">
						<div class="param-info">
						  <span>Max</span>
						  <input type="number" v-model.number="colorVmax" class="param-val-input">
						</div>
						<input type="range" v-model.number="colorVmax" min="-3000" max="3000" step="100" class="modern-slider">
					  </div>
					</div>

					<div class="opt-group" v-else-if="analysisVariable === 'count'">
					  <label class="group-label">Colour Scale Limit (# of measurements)</label>
					  <div class="param-item">
						<div class="param-info">
						  <span>Max</span>
						  <input type="number" v-model.number="colorVmax" class="param-val-input">
						</div>
						<input type="range" v-model.number="colorVmax" min="0" max="5000" step="100" class="modern-slider">
					  </div>
					</div>

					<div class="opt-group" v-else-if="analysisVariable === 'trend'">
					  <label class="group-label">Colour Scale Limit (m/yr/yr)</label>
					  <div class="param-item">
						<div class="param-info">
						  <span>Min</span>
						  <input type="number" v-model.number="colorVmin" class="param-val-input">
						</div>
						<input type="range" v-model.number="colorVmin" min="-500" max="500" step="10" class="modern-slider">
					  </div>
					  <div class="param-item" style="margin-top: 10px;">
						<div class="param-info">
						  <span>Max</span>
						  <input type="number" v-model.number="colorVmax" class="param-val-input">
						</div>
						<input type="range" v-model.number="colorVmax" min="-500" max="500" step="10" class="modern-slider">
					  </div>
					</div>
					
				</template>
				
			  </div>
			  
			    <div v-if="activeMode === 'analysis'" class="card-footer">
					<hr class="divider">
					<button 
						class="btn-run-analysis" 
						@click="runAnalysis" 
						:disabled="isMapBusy || !selectedSource"
					  >
						<div v-if="isMapBusy" class="btn-spinner"></div>
						
						<span>
						  {{ isMapBusy ? 'Processing Data...' : 'Update Analysis Map' }}
						</span>
					  </button>
				</div>
					
			</div>
		  </div>
		
		
		<div v-if="showAdvanced" class="advanced-popup-container">
			<div class="advanced-card">

				<div class="card-header">
					  <strong>Advanced Options</strong>
					  <div class="header-actions">
						<button @click="restoreDefaults" class="btn-restore-link">
						  Restore Defaults
						</button>
						<button @click="showAdvanced = false" class="popup-close">&times;</button>
					  </div>
				</div>
				
				<div class="card-body custom-scrollbar">

				<div class="opt-group">
					<label class="group-label">Variables</label>
					<div class="checkbox-grid">
					   <label v-for="v in availableVariable" :key="v" class="checkbox-pill">
						 <input type="checkbox" :value="v" v-model="pendingVariable"> 
						 <span>{{ v }}</span>
					   </label>
					</div>
				</div>
				
				<div class="opt-group">
					<div class="group-header">
						<label class="group-label">Data Sources</label>
						<div class="bulk-actions">
							<button type="button" class="bulk-btn" @click="selectAllSources">Select All</button>
							<button type="button" class="bulk-btn" @click="unselectAllSources">Unselect All</button>
						</div>
					</div>
					<div class="checkbox-grid">
					   <label v-for="s in availableSources" :key="s" class="checkbox-pill">
						 <input type="checkbox" :value="s" v-model="pendingSources"> 
						 <span>{{ formatSourceName(s) }}</span>
					   </label>
					</div>
				</div>
				
				<hr class="divider">
		
				<div class="opt-group">
					<label class="group-label">Parameters</label>
			
					<div class="param-item">
						<div class="param-info">
							<span>Buffer (m)</span>
							<span class="param-val">{{ pendingBuffer }}m</span>
						</div>
						<input type="range" v-model.number="pendingBuffer" min="0" max="5000" step="50" class="modern-slider">
					</div>
			
					<div class="param-item">
						<div class="param-info">
							<span>Gap Fill (Days)</span>
							<span class="param-val">{{ pendingSmoothingParams.gap }}</span>
						</div>
						<input type="range" v-model.number="pendingSmoothingParams.gap" min="1" max="120" class="modern-slider">
					</div>

					<div class="param-item">
						<div class="param-info">
							<span>Window Size (Points)</span>
							<span class="param-val">{{ pendingSmoothingParams.win_raw }}</span>
						</div>
						<input type="range" v-model.number="pendingSmoothingParams.win_raw" min="1" max="121" step="2" class="modern-slider">
					</div>
			
					<div class="param-item">
						<div class="param-info">
							<span>Window Size (Line)</span>
							<span class="param-val">{{ pendingSmoothingParams.win_daily }}</span>
						</div>
						<input type="range" v-model.number="pendingSmoothingParams.win_daily" min="1" max="121" step="2" class="modern-slider">
					</div>

					 <div class="param-item">
						<div class="param-info">
							<span>Polynomial Order</span>
							<span class="param-val">{{ pendingSmoothingParams.poly }}</span>
						</div>
						<input type="range" v-model.number="pendingSmoothingParams.poly" min="1" max="5" class="modern-slider">
					</div>
				</div>
				
			</div>
			
			<div class="card-footer">
			   <button class="btn-primary-action" @click="applyAdvancedOptions" :disabled="isFetching">
				   <span v-if="isFetching" class="spinner-small"></span>
				   <span v-else>Update All Timeseries</span>
			   </button>
			</div>
			
		  </div>
		</div>
			
	</div>
	
	<div class="resize-handle" @mousedown.prevent="startDrag" @touchstart.prevent="startDrag">
       <div class="handle-grip"></div>
    </div>

    <div class="bottom-dashboard" :style="{ height: (100 - mapHeightPercent) + '%' }">
  
		<div class="chart-section">
		  
			<div class="chart-controls-overlay" v-if="selectedPoints.length > 0 && plotOptions.length > 1">
				<span class="overlay-label">Graph View:</span>
				<select v-model="currentPlotVariable" @change="updateChart" class="overlay-select">
				   <option v-for="opt in plotOptions" :key="opt.val" :value="opt.val">
					   {{ opt.label }}
				   </option>
				</select>
			</div>
				
			<div class="custom-legend" v-if="legendItems.length > 0">
				
				<div class="legend-global-key">
				   <div class="key-item">
					  <span class="symbol-dot"></span><span>Points</span>
				   </div>
				   <div class="key-item">
					  <span class="symbol-line"></span><span>Daily</span>
				   </div>
				   <div class="key-item" v-if="showTrends">
					  <span class="symbol-dash"></span><span>Trend</span>
				   </div>
				</div>
					
				<div 
				   v-for="item in legendItems" 
				   :key="item.id" 
				   class="legend-item"
				   :class="{ 'is-hidden': !item.isVisible }"
				   @click="togglePointVisibility(item.id)"
				>
				   <span class="legend-label" :style="{ color: item.color }">
					  {{ item.label }}
				   </span>
				   
				   <span 
						  v-if="item.trendText" 
						  class="legend-trend" 
						  :style="{ color: item.color }"
						  v-html="item.trendText"
					></span>
				</div>
			</div>
				
			<div id="velocity-chart" class="chart-container"></div>
				
			<div id="chart-axis-controls" class="axis-controls" v-if="selectedPoints.length > 0">
				<div class="axis-group">
					<label><strong>Chart options:</strong></label>
				</div>
				
				<div class="axis-group">
					<label>Y-Min:</label>
					<input type="number" step="any" v-model.lazy="yAxisMin" @change="updatePlotAxes" />
					<label>Y-Max:</label>
					<input type="number" step="any" v-model.lazy="yAxisMax" @change="updatePlotAxes" />
				</div>
					
				<div class="axis-group">
					<label>Start:</label>
					<input type="date" v-model.lazy="xAxisMin" :min="minChartDate" :max="maxChartDate" @change="updatePlotAxes" />
					<label>End:</label>
					<input type="date" v-model.lazy="xAxisMax" :min="minChartDate" :max="maxChartDate" @change="updatePlotAxes" />
				</div>
				<button @click="resetAxes" class="btn-reset-axes">Reset</button>
					
				<div style="width: 1px; height: 20px; background: #ccc; margin: 0 5px;"></div>
					
				<div class="trend-group">
					<button 
					      id="btn-toggle-trends"
						  @click="toggleTrends" 
						  class="btn-icon" 
						  :class="{ 'active': showTrends }"
						  title="Calculate Trend"
						>
						  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<line x1="2" y1="20" x2="22" y2="4" />
								<circle cx="6" cy="15" r="2" fill="currentColor" stroke="none" />
								<circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
								<circle cx="18" cy="9" r="2" fill="currentColor" stroke="none" />
						  </svg>
					</button>
						
					<div v-if="showTrends" style="display:flex; gap:5px; align-items:center;">
						<label>Range:</label>
						<input type="text" v-model.lazy="trendStart" @change="updateTrendCalc" placeholder="Start" class="trend-input"/>
						<span>-</span>
						<input type="text" v-model.lazy="trendEnd" @change="updateTrendCalc" placeholder="End" class="trend-input"/>
					</div>
				</div>
					
			</div>
				
		</div>

		<div class="info-sidebar" v-if="selectedPoints.length > 0">
			
			<div class="info-header">
				<strong>Site List</strong>
			   <button @click="clearAll" class="btn-text-only">Clear All</button>
			</div>

			<div class="info-list-container">
			  <table class="points-table">
				<thead>
				   <tr>
					 <th style="width:8px">#</th>
					 <th>Lat</th>
					 <th>Lon</th>
					 <th>Buffer (m)</th>
					 <th style="width:8px"></th>
				   </tr>
				</thead>
				<tbody>
				  <tr v-for="(point, index) in selectedPoints" :key="point.id">
					 <td :style="{ color: point.color, fontWeight: 'bold', fontSize: '1.1em', textAlign: 'center' }" > {{ index + 1 }} </td>
					 <td><input type="number" v-model.number="point.lat" step="0.001" @change="refreshPointData(point)"></td>
					 <td><input type="number" v-model.number="point.lon" step="0.001" @change="refreshPointData(point)"></td>
					 <td><input type="number" v-model.number.lazy="point.buffer" min="0" step="50" class="table-input" style="text-align: right;" @change="refreshPointData(point)" > </td>
					 <td>
					   <button @click.stop="removePoint(point.id)" class="btn-remove-icon">&times;</button>
					 </td>
				  </tr>
				</tbody>
			  </table>
			</div>

		  </div>
		  
		  <div class="info-sidebar empty" v-else>
			 <p>Select points on the map or upload a file to view data.</p>
		  </div>

		</div>
	
    </div> 
  
  <div v-if="showHelp" class="modal-overlay" @click.self="showHelp = false">
      <div class="modal-content">
        <button class="modal-close" @click="showHelp = false">&times;</button>
        
        <h2>How to use SHIVER - Timeseries Explorer</h2>
	    <p>This gives a brief overview of the SHIVER Timeseries Explorer. Take a look at our <AppLink to="/documentation" class="text-link"><strong>SHIVER documentation</strong></AppLink> pages for more details.</p>
        
		<p>Or play the tutorials below to see all of the SHIVER Timeseries functions</p>
		
		<div class="action-buttons" style="display: flex; gap: 15px; margin-bottom: 20px;">
			<button class="play-tutorial-btn" @click="isVideoModalOpen = true">
			  <svg 
				xmlns="http://www.w3.org/2000/svg" 
				width="16" 
				height="16" 
				viewBox="0 0 24 24" 
				fill="currentColor"
				class="play-icon"
			  >
				<path d="M5 3l14 9-14 9V3z"/>
			  </svg>
			  Play Video Tutorial
			</button>
			
			<button class="play-tutorial-btn" @click="replayTour">
				<svg 
				  xmlns="http://www.w3.org/2000/svg" 
				  width="16" 
				  height="16" 
				  viewBox="0 0 24 24" 
				  fill="none" 
				  stroke="currentColor" 
				  stroke-width="2" 
				  stroke-linecap="round" 
				  stroke-linejoin="round"
				  class="play-icon"
				>
				  <polyline points="1 4 1 10 7 10"></polyline>
				  <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
				</svg>
				Replay Welcome Tour
			</button>
		</div>
		
        <div class="modal-body">
          <h3>1. Basic Usage</h3>
		  <ul>
            <li>Click anywhere on the map to extract a timeseries of ice velocity in that location. Up to 10 points can be selected.</li>
			<li>Navigate to your preferred ice sheet by clicking the Greenland button (<greenlandIcon class="inline-icon"/>)
			or the Antarctica button (<antarcticaIcon class="inline-icon"/>)</li>
		  </ul>
		   
		  <h3>2. Advanced Usage</h3>
		  <ul>
		     <li>Click and drag your extraction locations, or modify their coordinates and buffer using the Site List table.</li>
			 <li>Upload a file by clicking the
			    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
				<polyline points="17 8 12 3 7 8" />
				<line x1="12" y1="3" x2="12" y2="15" />
			    </svg>
			    symbol. KMZ, KML, GeoJSON or a zipped shapefile (containing .shp, .shx, .dbf, and .prj files) can be uploaded. The projection must be EPSG:4326 (WGS84).</li>
			 <li>Overlay any map of ice motion, add glacier basin outlines or calculate speed change over any time period using the "Map Layers & Analysis" tool 
                (<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
				<polyline points="2 12 12 17 22 12"></polyline>
				<polyline points="2 17 12 22 22 17"></polyline>
			    </svg>)</li>
			 <li>Choose which data to extract and how to process it using the "Advanced Options" tool
			    (<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84a.484.484 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.488.488 0 0 0-.59.22L2.09 8.83a.488.488 0 0 0 .12.61l2.03 1.58c-.05.3-.07.63-.07.94s.02.64.07.94l-2.03 1.58a.488.488 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.27.41.48.41h3.84c.24 0 .44-.17.48-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.488.488 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>)</li>
			 <li>Add a linear trend line to your graph by clicking the 
			    <svg style="width:1.2em;vertical-align:text-bottom" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="20" x2="22" y2="4"/><g stroke="none" fill="currentColor"><circle cx="6" cy="15" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="18" cy="9" r="2"/></g></svg>
			    button below the graph. A * symbol in the legend indicates the trend is significant.</li>
			 <li>Colour the graph data by data source by clicking the palette symbol (<svg class="inline-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
			    <path fill="currentColor" d="M12,2C6.48,2,2,6.48,2,12s4.48,10,10,10c1.21,0,2.12-1.07,1.86-2.26c-0.08-0.34-0.24-0.66-0.45-0.92 C13.2,18.55,13.06,18.27,13.06,18c0-0.55,0.45-1,1-1h1.56c3.53,0,6.38-2.85,6.38-6.38C22,5.46,17.52,2,12,2z M6.5,11.5 c-0.83,0-1.5-0.67-1.5-1.5s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S7.33,11.5,6.5,11.5z M9.5,7.5C8.67,7.5,8,6.83,8,6s0.67-1.5,1.5-1.5 s1.5,0.67,1.5,1.5S10.33,7.5,9.5,7.5z M14.5,7.5C13.67,7.5,13,6.83,13,6s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S15.33,7.5,14.5,7.5z M17.5,11.5c-0.83,0-1.5-0.67-1.5-1.5s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S18.33,11.5,17.5,11.5z"/>
			    </svg>)</li>
			 <li>Download the graph (<graphIcon class="inline-icon"/>) or data (<excelIcon class="inline-icon"/>)</li>
		   </ul>
			
        </div>
      </div>
    </div>
	
	<VideoModal 
    :isOpen="isVideoModalOpen"
    title="SHIVER Timeseries Explorer Tutorial"
    :videoSrc="tutorialVideoSrc"
    @close="isVideoModalOpen = false"
  />
	
</template>

<script setup>
// --- IMPORTS ---
import { ref, shallowRef, computed, nextTick, watch, onMounted, onUnmounted, inject, markRaw } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import "leaflet/dist/leaflet.css";
import { LMap, LWmsTileLayer, LTileLayer, LCircleMarker, LGeoJson, LControlLayers, LLayerGroup, LControlScale, LRectangle, LTooltip } from "@vue-leaflet/vue-leaflet";
import axios from 'axios';
//import Plotly from 'plotly.js-dist-min'; 
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
// import L from 'leaflet';
//import domtoimage from 'dom-to-image-more';
import * as XLSX from 'xlsx';
import antarcticaIcon from '../components/icons/antarcticaIcon.vue';
import greenlandIcon from '../components/icons/greenlandIcon.vue';
import excelIcon from '../components/icons/excelIcon.vue';
import graphIcon from '../components/icons/graphIcon.vue';
import { generateCitationText } from '../utils/citationsConfig';
import { startGuestTour } from '../tours/guestTour';
import VideoModal from '../components/VideoModal.vue';
import { useHead } from '@unhead/vue'
const plotlyLib = ref(null)

// --- API CONFIGURATION ---
import apiClient, { API_URL } from '../api';

// --- PROJ4 SETUP ---
import proj4 from 'proj4';
//window.proj4 = proj4; // Crucial: proj4leaflet expects proj4 to be globally available in Vite!
//import 'proj4leaflet';
const L = shallowRef(null);
const crsGreenland = shallowRef(null)
const crsAntarctica = shallowRef(null)
const isMapReady = ref(false)

// --- SEO --- //
useHead({
  title: 'SHIVER | Interactive Timeseries Explorer',
  meta: [
    { 
      name: 'description', 
      content: 'Measure speed change, speed trends and explore time-series of ice velocity data from multiple Earth Observation missions for the Greenland Ice Sheet and Antarctic Ice Sheet.' 
    }
  ]
})

// --- NATIVE GOOGLE ANALYTICS TRACKING ---
const trackEvent = (eventName, params = {}) => {
  if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
    window.gtag('event', eventName, params);
    console.log(`GA Event Sent: ${eventName}`, params);
  } else {
    console.log(`GA Event Skipped (Not loaded or server-side): ${eventName}`);
  }
};


// --- URL UPDATE --- //
const route = useRoute();
const router = useRouter();

// Sync URL
const syncUrl = () => {
  // 1. Get Points
  const pointStrings = selectedPoints.value.map(pt => {
    const bufferToUse = pt.buffer || pt.settings?.buffer || pendingBuffer.value;
    return `${parseFloat(pt.lat).toFixed(4)},${parseFloat(pt.lon).toFixed(4)},${bufferToUse}`;
  });

  // 2. Get Map View (Safely fallback to current reactive variables)
  const currentZoom = zoom.value;
  let currentCenterStr = '';
  
  // center.value could be an array [lat, lng] or an object {lat, lng} depending on Leaflet state
  if (Array.isArray(center.value)) {
    currentCenterStr = `${parseFloat(center.value[0]).toFixed(4)},${parseFloat(center.value[1]).toFixed(4)}`;
  } else if (center.value && center.value.lat !== undefined) {
    currentCenterStr = `${parseFloat(center.value.lat).toFixed(4)},${parseFloat(center.value.lng).toFixed(4)}`;
  }

  // 3. Construct the query object dynamically
  const newQuery = {
    reg: currentRegion.value,
    z: currentZoom,
    c: currentCenterStr
  };

  // Only add 'p' to the URL if there are actually points on the map
  if (pointStrings.length > 0) {
    newQuery.p = pointStrings;
  }

  // 4. Overwrite URL
  router.replace({
    path: route.path,
    query: newQuery
  });
};

// Zoom to URL if one has just been copied
onMounted(async () => {
  await nextTick(); 
  
  // 1. LAZY-LOAD PLOTLY (Safe from the SSG build server)
  const plotlyModule = await import('plotly.js-dist-min');
  // Handle potential differences in how the bundler exports the minified module
  plotlyLib.value = plotlyModule.default || plotlyModule;
  
  // 2. Dynamically import Leaflet
  const leafletModule = await import('leaflet');
  L.value = leafletModule.default || leafletModule;

  // 3. Now that we are safely in the browser, attach proj4 to the window
  window.proj4 = proj4;

  // 4. Dynamically import proj4leaflet ONLY AFTER Leaflet and window.proj4 are ready
  await import('proj4leaflet');
  
  // 5 Custom projections
  crsGreenland.value = markRaw(new L.value.Proj.CRS(
		'EPSG:3413',
		'+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs',
		{
		  resolutions: [8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1],
		  origin: [-4194304, 4194304]
		}
   ));

  crsAntarctica.value = markRaw(new L.value.Proj.CRS(
		'EPSG:3031',
		'+proj=stere +lat_0=-90 +lat_ts=-71 +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs',
		{
		  resolutions: [8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1],
		  origin: [-4194304, 4194304]
		}
   ));

  // 1. DETERMINE THE TRUE REGION FIRST
  const urlRegion = route.query.reg;
  const pointsQuery = route.query.p;
  let targetRegion = 'Greenland'; // Default assumption

  if (urlRegion === 'Greenland' || urlRegion === 'Antarctica') {
    targetRegion = urlRegion;
  } else if (pointsQuery) {
    // If no reg param, infer the region from the first point's latitude
    const firstPoint = Array.isArray(pointsQuery) ? pointsQuery[0] : pointsQuery;
    const lat = parseFloat(firstPoint.split(',')[0]);
    if (!isNaN(lat)) {
      targetRegion = lat < 0 ? 'Antarctica' : 'Greenland';
    }
  }
  // Set it without triggering a reset
  currentRegion.value = targetRegion;

  // 2. SET THE MAP VIEW (Zoom & Center)
  if (route.query.z && route.query.c) {
    const zParam = parseInt(route.query.z, 10);
    const [cLat, cLon] = route.query.c.split(',').map(parseFloat);
    
    if (!isNaN(zParam) && !isNaN(cLat) && !isNaN(cLon)) {
       zoom.value = zParam;
       center.value = [cLat, cLon];
    }
  } else {
    // If no view is in the URL, apply defaults for the target region
    if (currentRegion.value === 'Greenland') {
      center.value = [71.394, -40.987]; zoom.value = 1;
    } else {
      center.value = [-87.82, 87.09]; zoom.value = 0;
    }
  }

  // 3. FLIP THE SWITCH TO RENDER THE MAP
  // Because zoom and center are set, the map will spawn perfectly aligned!
  isMapReady.value = true;
  await nextTick(); 

  // 4. LOAD POINTS
  if (pointsQuery) {
    const points = Array.isArray(pointsQuery) ? pointsQuery : [pointsQuery];

    for (const pt of points) {
      const [latStr, lngStr, bufferStr] = pt.split(',');
      const lat = parseFloat(latStr);
      const lng = parseFloat(lngStr);
      const pointBuffer = bufferStr ? parseInt(bufferStr, 10) : pendingBuffer.value;

      if (!isNaN(lat) && !isNaN(lng)) {
        // We already forced the region in Step 1, so this will rarely trip.
        // But if a URL has mixed Greenland/Antarctica points, it acts as a safeguard.
        const calculatedRegion = lat < 0 ? 'Antarctica' : 'Greenland';
        if (currentRegion.value !== calculatedRegion) {
          currentRegion.value = calculatedRegion;
          switchRegion(false); 
        }
        
        const safeCustomSettings = {
            sources: [...pendingSources.value],
            buffer: pointBuffer,
            variable: [...pendingVariable.value],
            smoothing: { ...pendingSmoothingParams.value }
        };

        const newId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        await fetchSinglePoint(newId, lat, lng, COLORS[0], safeCustomSettings); 
      }
    }
  }
});


// --- POINT DRAGGING FUNCTIONS --- //
// 1. Start Dragging (Attached to Rectangle AND Circle)
const startPointDrag = (e, index) => {
  // Prevent the click from bubbling to the map (prevents creating a new point)
  L.value.DomEvent.stopPropagation(e);
  L.value.DomEvent.preventDefault(e);

  // Disable map panning so the map stays still while we move the box
  if (map.value && map.value.leafletObject) {
    map.value.leafletObject.dragging.disable();
  }
  
  // Set the global cooldown flag immediately
  isDragCooldown.value = true;
  
  // Make sure we use the current version of this point (with the latest coordinates)
  const freshPoint = selectedPoints.value[index];

  // Calculate the difference between the mouse cursor and the shape's center
  // This ensures the shape moves smoothly relative to where you grabbed it
  const mouseLat = e.latlng.lat;
  const mouseLng = e.latlng.lng;

  draggingState.value = {
    active: true,
    point: freshPoint, // Reference to the reactive point object
    offsetLat: freshPoint.lat - mouseLat,
    offsetLon: freshPoint.lon - mouseLng,
	startLat: freshPoint.lat,
    startLon: freshPoint.lon
  };
};

// 2. Move (Attached to the MAP)
const onMapMouseMove = (e) => {
  if (!draggingState.value.active) return;
  
  const state = draggingState.value;
  
  // Find the index of the point we are dragging
  // We use findIndex because we are about to replace the object, 
  // so we need its location in the array.
  const index = selectedPoints.value.findIndex(p => p.id === state.point.id);
  
  if (index === -1) return;

  // 1. Calculate new coordinates
  const newLat = e.latlng.lat + state.offsetLat;
  const newLon = e.latlng.lng + state.offsetLon;

  // 2. Create a new object (Copy + Update)
  // This breaks the reference to the old object. 
  // Vue Production cannot ignore this—it sees a completely new piece of data.
  const updatedPoint = {
      ...selectedPoints.value[index], // Copy existing properties (color, name, etc.)
      lat: newLat,
      lon: newLon
  };

  // 3. Swap the old point for the new one using splice
  // splice matches the array mutation methods Vue watches closely
  selectedPoints.value.splice(index, 1, updatedPoint);

  // 4. Update our drag state to track the new object
  // If we don't do this, 'state.point' will still point to the old (stale) object
  state.point = updatedPoint;
};

// 3. End Drag (Attached to the map)
const onMapMouseUp = async (e) => {
  if (!draggingState.value.active) return;

  // Re-enable map panning
  if (map.value && map.value.leafletObject) {
    map.value.leafletObject.dragging.enable();
  }
  
  // 1. Extract values before resetting the state
  const point = draggingState.value.point;
  const startLat = draggingState.value.startLat;
  const startLon = draggingState.value.startLon;

  // 2. Full State Reset (Cleaner)
  draggingState.value = { 
    active: false, 
    point: null, 
    offsetLat: 0, 
    offsetLon: 0,
    startLat: 0,
    startLon: 0
  };
  
  // Only fetch if the point moved significantly
  const hasMoved = Math.abs(point.lat - startLat) > 0.0001 || Math.abs(point.lon - startLon) > 0.0001;

  if (hasMoved) {
	  syncUr(); // update the URL to reflect the new points location
      await fetchSinglePoint(point.id, point.lat, point.lon, point.color, point.settings);
  }

  // 2. Clear the cooldown flag after a short delay
  // This ensures the subsequent 'click' event (which happens ~10ms later) 
  // is still blocked by onMapClick
  setTimeout(() => {
      isDragCooldown.value = false;
  }, 100);
};

// 4. Stops clicks on the feature from bubbling up to the map
const stopPropagation = (e) => {
  // L.DomEvent.stopPropagation works on the native event wrapped inside the Leaflet event
  if (e.originalEvent) {
    L.value.DomEvent.stopPropagation(e.originalEvent);
  } else {
    L.value.DomEvent.stopPropagation(e);
  }
};

// --- FEEDBACK POPUP STATE ---
// The main trigger function
const triggerFeedbackPopup = () => {
  if (typeof window === 'undefined') return;
  const hasShown = sessionStorage.getItem(STORAGE_KEY);
  if (!hasShown) {
    showFeedbackPopup.value = true;
    sessionStorage.setItem(STORAGE_KEY, 'true');
    cleanupTriggers();  // Once triggered, we can stop listening for exit intent or time
  }
};

// Exit Intent Handler
const handleExitIntent = (event) => {
  // We check if clientY <= 0. This detects if the mouse moves OUT 
  // of the top of the viewport (towards tabs/address bar).
  // This prevents the popup from showing if they just move the mouse 
  // to a second monitor on the right/left.
  if (event.clientY <= 0) {
    triggerFeedbackPopup();
  }
};

const closeFeedbackPopup = () => {
  showFeedbackPopup.value = false;
};

// Clean up listeners to prevent memory leaks or errors
const cleanupTriggers = () => {
  if (timerInstance) clearTimeout(timerInstance);
  document.removeEventListener('mouseleave', handleExitIntent);
};

onMounted(() => {
  // Check immediately if we've already shown it this session (e.g. on page refresh)
  // If yes, do nothing. If no, start the listeners.
  if (!sessionStorage.getItem(STORAGE_KEY)) {
    // 1. Set the time-based trigger
    timerInstance = setTimeout(() => {
      triggerFeedbackPopup();
    }, TIME_DELAY_MS);
    // 2. Set the exit-intent trigger
    document.addEventListener('mouseleave', handleExitIntent);
  }
});

onUnmounted(() => {
  cleanupTriggers(); // Good practice to clean up when the component is destroyed
});


// --- CONSTANTS ---
// Colors for selected points (cycles through this list)
const COLORS = [
  'rgb(1, 25, 89)', 'rgb(14, 55, 94)', 'rgb(28, 85, 97)', 
  'rgb(62, 108, 85)', 'rgb(105, 123, 62)', 'rgb(154, 136, 46)', 
  'rgb(213, 148, 72)', 'rgb(249, 163, 129)', 'rgb(253, 183, 189)', 'rgb(250, 204, 250)'
];

// - Colour by data source - 
const colorBySource = ref(false);
// Master color mapping for ALL possible data sources
const FIXED_SOURCE_COLORS = {
  // Shared
  'SHIFT': 'rgb(0, 0, 0)',           // Black
  'ITS_LIVE_annual': 'rgb(153,50,204)', // dark orchid
  
  // Greenland
  'PROMICE': 'rgb(119,136,153)',        // light slate gray
  'MEaSUREs_monthly': 'rgb(0,128,0)',       // green
  'MEaSUREs_quarterly': 'rgb(34,139,34)',       // forest green
  'MEaSUREs_winter': 'rgb(154,205,50)',       // yellow green
  'MEaSUREs_annual': 'rgb(0,100,0)',       // dark green
  'Mouginot_annual': 'rgb(60,179,113)', // medium sea green
  'C3S_annual': 'rgb(255,69,0)', // orangered
  'ESA_CCI_winter': 'rgb(255,160,122)',// light salmon
  'ESA_CCI_Sentinel-1': 'rgb(250,128,114)', // salmon
  'ESA_CCI_Sentinel-2': 'rgb(205,92,92)',  // indian red
  'ESA_CCI_CSK': 'rgb(220,20,60)',    // crimson
  'ESA_CCI_ERS1-2_Envisat': 'rgb(178,34,34)', // firebrick
  'ESA_CCI_ERS2_1995-1996': 'rgb(255,0,0)', // red
  'ESA_CCI_PALSAR': 'rgb(139,0,0)', // dark red
  'ESA_CCI_ERS1_1991-1992': 'rgb(139,0,0)', // tomato

  // Antarctica
  'ENVEO_monthly': 'rgb(70,130,180)',   // steel blue
  'MEaSUREs_annual': 'rgb(0,100,0)', // dark green
  'MEaSUREs_multiyear': 'rgb(46,139,87)', // sea green
  'MEaSUREs_ASE': 'rgb(107,142,35)',  // olivedrab
  'SID_annual': 'rgb(255,215,0)',      // gold
  'C3S_annual': 'rgb(255,69,0)', // orangered
  'Joughin_Sentinel-1': 'rgb(138,43,226)', // blue violet
  'Joughin_TSX': 'rgb(148,0,211)',   // dark violet
  'Li_Totten': 'rgb(140, 109, 49)',      // Bronze
  'ENVEO_Sentinel-1_PIG': 'rgb(189, 158, 57)', // Gold
  'ENVEO_ERS': 'rgb(65,105,225)',      // royal blue
  'ENVEO_TSX': 'rgb(0,0,255)',     // blue
  'ENVEO_PALSAR': 'rgb(0,0,205)',      // medium blue
  'ENVEO_TSX_Sentinel-1': 'rgb(0,0,139)',    // dark blue
  'ENVEO_TSX_PALSAR': 'rgb(30,144,255)', // dodger blue
  'Rosanova_PIG74': 'rgb(0, 128, 128)',        // teal
  'Scambos_PIG87': 'rgb(0, 139, 139)',         // dark cyan
  'Joughin_PIG_ERS': 'rgb(32, 178, 170)',      // light sea green
  'Bohlander_Scambos02': 'rgb(95, 158, 160)',  // cadet blue
  'Bindschadler96': 'rgb(0, 206, 209)',        // dark turquoise
  'ScambosBohlander_DF': 'rgb(72, 209, 204)',  // medium turquoise
  'Scambos04': 'rgb(64, 224, 208)',            // turquoise
  'Brecher82': 'rgb(0, 255, 255)',             // cyan
  'Vaughan96': 'rgb(175, 238, 238)'            // pale turquoise
};
const FALLBACK_COLORS = ['rgb(50, 50, 50)', 'rgb(100, 100, 100)', 'rgb(150, 150, 150)'];
let fallbackIdx = 0;
const sourceColorMap = {}; // Caches fallbacks so they stay consistent

const getSourceColor = (source) => {
    if (!source || source === 'N/A') return 'rgb(136, 136, 136)';
    // 1. Return the locked color if we defined it above
    if (FIXED_SOURCE_COLORS[source]) {
        return FIXED_SOURCE_COLORS[source];
    }
    // 2. Fallback for unknown sources
    if (!sourceColorMap[source]) {
        sourceColorMap[source] = FALLBACK_COLORS[fallbackIdx % FALLBACK_COLORS.length];
        fallbackIdx++;
    }
    return sourceColorMap[source];
};

// Helper to create transparent versions of the colors for fill/error bars
const makePale = (rgb) => rgb.replace('rgb', 'rgba').replace(')', ', 0.3)');

// --- REACTIVE STATE ---
const map = shallowRef(null);
const currentRegion = ref('Greenland');
const zoom = ref(1);
const center = ref([71.394, -40.987]);
const statusMessage = ref("");
const isDownloading = ref(false);
const isDownloadingChart = ref(false);
const isUploading = ref(false);
const selectedPoints = ref([]); 
const showHelp = ref(false); 
const isVideoModalOpen = ref(false);
const iceEdgeData = ref(null);
const groundingLineData = ref(null);
const mapHeightPercent = ref(60); 
const isDragging = ref(false);
const isFetching = ref(false);
const isRefreshing = ref(false);
const showTrends = ref(false);
const trendStart = ref(''); // YYYY-MM-DD
const trendEnd = ref('');   // YYYY-MM-DD
const legendItems = ref([]);
const isUserZoomed = ref(false);
const TIME_DELAY_MS = 90000; // 1.5 Minutes 
const STORAGE_KEY = 'shiver_feedback_shown';
const showFeedbackPopup = ref(false);
const isMessageSpinnerRequired = ref(false);  // Optional: controls the spinner
const requireLogin = inject('requireLogin');
let timerInstance = null;
let messageTimeout = null;

// --- OVERLAY LAYERS --- //
// Layer manager
const selectedBasemap = ref('none');
const showLayerManager = ref(false); 
const isMapBusy = ref(false);
const isManualUpdate = ref(false);
const activeMode = ref('overview');
const analysisWmsUrl = ref('');
const selectedSource = ref('');
const selectedEpoch = ref('');
const allEpochs = ref([]);
const datasetVersion = ref(null);
const isLoadingMetadata = ref(false);
const showSatelliteBasemap = computed(() => selectedBasemap.value === 'satellite');
const overlayLayer = ref('speed'); // Defaults to speed
const isFlowActive = ref(false);
const showMargins = ref(false);
const toggleBasemap = (val) => {
  // Intercept the click for Antarctica satellite
  if (val === 'satellite' && currentRegion.value === 'Antarctica') {
    statusMessage.value = "No satellite basemap available for Antarctica.";
    return; // Stop execution here
  }
  // If clicking the currently active one, turn it off. Otherwise, set it to the new value.
  selectedBasemap.value = selectedBasemap.value === val ? 'none' : val;
};
const toggleOverlay = (val) => {
  overlayLayer.value = overlayLayer.value === val ? 'none' : val;
};
const toggleBasin = (val) => {
  // If clicking the active basin, turn it off ('none'). Otherwise, select it.
  selectedBasinId.value = selectedBasinId.value === val ? 'none' : val;
};
watch(showMargins, (isVisible) => {
  // If turned on, and we haven't fetched the data yet, go get it!
  if (isVisible && !iceEdgeData.value) {
    loadMarginData();
  }
});

// --- ANALYSIS LAYERS --- //
const analysisVariable = ref('speed');
const isDifferenceMode = ref(false);
const compareEpoch = ref('');
const compareSource = ref('');
const colorVmax = ref(3000);
const colorVmin = ref(-500);
// Filter the epochs based on the user's dropdown selection
const filteredEpochs = computed(() => {
  if (!allEpochs.value) return [];
  if (selectedSource.value === 'all' || !selectedSource.value) {
    return allEpochs.value;
  }
  return allEpochs.value.filter(e => e.source === selectedSource.value);
});
// 4. Calculate the Long-term Average label
const longTermAverageLabel = computed(() => {
  const epochs = filteredEpochs.value;
  if (!epochs || epochs.length === 0) return 'Long-term average';
  let minDate = epochs[0].start_date;
  let maxDate = epochs[0].end_date;
  for (const ep of epochs) {
    if (ep.start_date < minDate) minDate = ep.start_date;
    if (ep.end_date > maxDate) maxDate = ep.end_date;
  }
  return `Long-term average (${minDate} to ${maxDate})`;
});

// Filter the reference epochs based on the user's dropdown selection
const filteredCompareEpochs = computed(() => {
  if (!allEpochs.value) return [];
  if (compareSource.value === 'all' || !compareSource.value) {
    return allEpochs.value;
  }
  return allEpochs.value.filter(e => e.source === compareSource.value);
});
// 4. Calculate the Long-term Average label
const longTermAverageLabelCompare = computed(() => {
  const compareEpochs = filteredCompareEpochs.value;
  if (!compareEpochs || compareEpochs.length === 0) return 'Long-term average';
  let minCompareDate = compareEpochs[0].start_date;
  let maxCompareDate = compareEpochs[0].end_date;
  for (const ep of compareEpochs) {
    if (ep.start_date < minCompareDate) minCompareDate = ep.start_date;
    if (ep.end_date > maxCompareDate) maxCompareDate = ep.end_date;
  }
  return `Long-term average (${minCompareDate} to ${maxCompareDate})`;
});

// Fetch metadata
const fetchLayerMetadata = async () => {
  isLoadingMetadata.value = true;
  allEpochs.value = []; // Clear old data while loading
  
  try {
    // Ping the backend
    const baseUrl = API_URL.replace(/\/$/, '');
    const url = `${baseUrl}/api/analysis/metadata/${currentRegion.value}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    allEpochs.value = data.epochs;
	
	// Store the dataset version retrieved from backend
    datasetVersion.value = data.dataset_version || null;
    
    console.log(`Loaded ${allEpochs.value.length} epochs for ${currentRegion.value} (v${datasetVersion.value})`);
	
    // Optional QoL: If the previously selected source doesn't exist in the new region, clear it.
    if (selectedSource.value && !availableSources.value.includes(selectedSource.value)) {
      selectedSource.value = '';
      selectedEpoch.value = '';
      compareEpoch.value = '';
      compareSource.value = ''; 
    } else if (compareSource.value && !availableSources.value.includes(compareSource.value)) {
      compareSource.value = '';
      compareEpoch.value = '';
    }
    
  } catch (error) {
    console.error("Failed to fetch layer metadata:", error);
  } finally {
    isLoadingMetadata.value = false;
  }
};

// Fetch automatically on loading
onMounted(() => {
  fetchLayerMetadata();
});

// Re-fetch automatically whenever the user clicks the Greenland/Antarctica toggle buttons
watch(currentRegion, (newRegion, oldRegion) => {
  if (newRegion !== oldRegion) {
    // If switching to Antarctica while satellite is on, turn it off
    if (newRegion === 'Antarctica' && selectedBasemap.value === 'satellite') { selectedBasemap.value = 'none'; }
    fetchLayerMetadata();
  }
});

// Format the epoch dates nicely
const formatEpochDates = (epoch) => {
  if (epoch.start_date === epoch.end_date) {
    return epoch.start_date; // Just show one date if they match
  }
  return `${epoch.start_date} to ${epoch.end_date}`;
};


// Watch for mode changes and set sensible defaults for the sliders
watch([analysisVariable, isDifferenceMode], ([newVar, newDiff]) => {
  if (newVar === 'speed' && !newDiff) {
    colorVmax.value = 3000; 
  } else if (newVar === 'speed' && newDiff) {
    colorVmin.value = -1000;
    colorVmax.value = 1000;
  } else if (newVar === 'count') {
    colorVmax.value = 500;
  } else if (newVar === 'trend') {
    colorVmin.value = -100;
    colorVmax.value = 100;
  }
});

// Trigger analysis
function runAnalysis() {
  if (!selectedSource.value) return;
  
  isMapBusy.value = true;
  isManualUpdate.value = true;
  statusMessage.value = "Running analysis...";

  const baseUrl = API_URL.replace(/\/$/, '');
  const params = new URLSearchParams({
    variable: analysisVariable.value,
    source: selectedSource.value,
    vmin: colorVmin.value,
    vmax: colorVmax.value,
    t: Date.now() // Safe here because it only fires on click
  });

  if (analysisVariable.value === 'speed') {
    if (selectedEpoch.value !== '') params.append('epoch', selectedEpoch.value);
    
    if (isDifferenceMode.value && compareEpoch.value && compareSource.value) {
      params.append('compareepoch', compareEpoch.value);
      params.append('comparesource', compareSource.value); 
    }
  }

  // Updating this ref triggers the Leaflet layer update
  analysisWmsUrl.value = `${baseUrl}/api/analysis/wms/${currentRegion.value}?${params.toString()}`;  
}

// Function to handle the successful load of tiles
const onAnalysisComplete = () => {
  if (!isManualUpdate.value) {
    isMapBusy.value = false;
    return;
  }

  // If it was a manual update, show the completion message
  statusMessage.value = "Analysis complete.";
  isMapBusy.value = false;
  
  // Disarm the flag so subsequent zooms stay quiet
  isManualUpdate.value = false;
};

// Function to handle errors
const onAnalysisError = () => {
  if (isManualUpdate.value) {
    statusMessage.value = "Error performing analysis.";
    isManualUpdate.value = false;
  }
  isMapBusy.value = false;
};

// In case the map triggers a reload internally
const onAnalysisLoading = () => {
  isMapBusy.value = true;
};


// Define analysis colours and labels
// Calculate exactly where zero falls as a percentage
const zeroPivotPercentage = computed(() => {
  const min = colorVmin.value;
  const max = colorVmax.value;
  
  if (min >= 0) return 0;
  if (max <= 0) return 100;
  
  const range = max - min;
  return (Math.abs(min) / range) * 100;
});

// 2. Update dynamicVikStyle to use the extracted percentage
const dynamicVikStyle = computed(() => {
  const min = colorVmin.value;
  const max = colorVmax.value;
  
  // If the user's limits don't cross zero, return a flat stretch
  if (min >= 0 || max <= 0) {
    return { background: 'linear-gradient(to right, #011261, #EBEDEA, #611200)' };
  }
  
  const zeroPct = zeroPivotPercentage.value;
  
  return {
    background: `linear-gradient(to right, 
      #011261 0%, 
      #2E7CA6 ${zeroPct / 2}%, 
      #EBEDEA ${zeroPct}%, 
      #AF8A3E ${zeroPct + (100 - zeroPct) / 2}%, 
      #611200 100%)`
  };
  
});


// -- MULTI ZARR ---
// Dictionary of data sources, labelled as stored in the zarr store
const REGION_SOURCES = {
  'Greenland': [
    'PROMICE', 'SHIFT', 'MEaSUREs_monthly', 'MEaSUREs_quarterly', 'MEaSUREs_winter', 
	'MEaSUREs_annual', 'C3S_annual', 'Mouginot_annual', 'ITS_LIVE_annual', 
    'ESA_CCI_winter', 'ESA_CCI_Sentinel-1', 'ESA_CCI_Sentinel-2', 'ESA_CCI_CSK', 
    'ESA_CCI_ERS1-2_Envisat', 'ESA_CCI_ERS2_1995-1996', 'ESA_CCI_PALSAR', 'ESA_CCI_ERS1_1991-1992'
  ],
  'Antarctica': [
    'ENVEO_monthly', 'ITS_LIVE_annual', 'MEaSUREs_annual', 'MEaSUREs_multiyear', 
    'MEaSUREs_ASE', 'SID_annual', 'C3S_annual', 'Joughin_Sentinel-1', 'Joughin_TSX', 
    'Li_Totten', 'ENVEO_Sentinel-1_PIG', 'ENVEO_ERS', 'ENVEO_TSX', 'ENVEO_PALSAR', 
    'ENVEO_TSX_Sentinel-1', 'ENVEO_TSX_PALSAR', 'SHIFT', 'Rosanova_PIG74', 
	'Scambos_PIG87', 'Joughin_PIG_ERS', 'Bohlander_Scambos02', 'Bindschadler96',
	'ScambosBohlander_DF', 'Scambos04', 'Brecher82', 'Vaughan96'
  ]
};
// Dinctionary linking actual data source name to advanced options display names. Only required for some data sources. Other just swap underscores for spaces
const SOURCE_DISPLAY_NAMES = {
    'ESA_CCI_ERS1-2_Envisat': 'ESA CCI ERS-1/2 & Envisat',
    'ESA_CCI_ERS2_1995-1996': 'ESA CCI ERS-2 (1995-1996)',
    'ESA_CCI_ERS1_1991-1992': 'ESA CCI ERS-1 (1991-1992)',
	'ESA_CCI_winter': 'ESA CCI (winter)',
	'C3S_annual': 'C3S (annual)',
	'SID_annual': 'SID (annual)',
	'ITS_LIVE_annual': 'ITS_LIVE (annual)',
    'Mouginot_annual': 'Mouginot (annual)',
	'MEaSUREs_monthly': 'MEaSUREs (monthly)',
	'MEaSUREs_annual': 'MEaSUREs (annual)',
	'MEaSUREs_quarterly': 'MEaSUREs (quarterly)',
	'MEaSUREs_winter': 'MEaSUREs (winter)',
	'MEaSUREs_multiyear': 'MEaSUREs (multi-year)',
	'MEaSUREs_ASE': 'MEaSUREs (ASE only)',
	'ENVEO_monthly': 'ENVEO (monthly)',
    'ENVEO_TSX_PALSAR': 'ENVEO TSX & PALSAR',
	'ENVEO_TSX_Sentinel-1': 'ENVEO TSX & Sentinel-1',
	'ENVEO_Sentinel-1_PIG': 'ENVEO Sentinel-1 pairs (Pine Island)',
	'Joughin_Sentinel-1': 'Joughin Sentinel-1 (quarterly)',
	'Rosanova_PIG74': 'Pine Island (1974)',
	'Scambos_PIG87': 'Pine Island (1987)',
	'Joughin_PIG_ERS': 'Pine Island (1992-2000)',
	'Bohlander_Scambos02': 'Sulzberger & Prestud (1986-1989)',
	'Bindschadler96': 'Ice Streams D & E (1985-1991)',
	'ScambosBohlander_DF': 'Ice Streams D & F (1984-1995)',
	'Scambos04': 'Institute (1986-1989)',
	'Brecher82': 'Byrd (1978-1979)',
	'Vaughan96': 'Filchner-Ronne (1968-1994)',
};
const formatSourceName = (rawName) => {
    if (rawName === 'all') { return 'All Sources'; }
    if (SOURCE_DISPLAY_NAMES[rawName]) {
        return SOURCE_DISPLAY_NAMES[rawName];
    }
    return rawName.replace(/_/g, ' '); 
};
// Define the UI list depending on user selected zarr options
const availableSources = computed(() => {
  const region = currentRegion.value || 'Greenland'; 
  return REGION_SOURCES[region] || [];
});
// Define a list specifically for the analysis window
const analysisDropdownSources = computed(() => {
  return ['all', ...availableSources.value];
});
// The list containing the actual options selected by the user
const pendingSources = ref([...(REGION_SOURCES[currentRegion.value || 'Greenland'] || [])]);
// Update the list in advanced options if the region changes
watch(currentRegion, (newRegion) => {
    pendingSources.value = [...(REGION_SOURCES[newRegion] || [])];
});
// Functions to select/deselect all data sources in advanced options:
const selectAllSources = () => {
    pendingSources.value = [...availableSources.value];
};
const unselectAllSources = () => {
    pendingSources.value = [];
};

// --- DYNAMIC CONFIGURATION ---
// These computed properties automatically feed the correct settings to the map 
// whenever `currentRegion` changes.
const currentCrs = computed(() => {
    return currentRegion.value === 'Antarctica' ? crsAntarctica.value : crsGreenland.value;
});


// --- BASE MAP --- //
const wmsBaseUrl = computed(() => {
  return currentRegion.value === 'Antarctica' 
    ? 'https://gibs.earthdata.nasa.gov/wms/epsg3031/best/wms.cgi' 
    : 'https://gibs.earthdata.nasa.gov/wms/epsg3413/best/wms.cgi';
});

const mapOptions = computed(() => ({
  zoomControl: false,
  crs: currentCrs.value,
  minZoom: 0,
  maxZoom: 10 // GIBS Blue Marble tiles generally stop rendering cleanly past zoom 6 or 7
}));


// Limited use functions
const MAX_FREE_CLICKS = 5;
// Initialize from storage (so refreshing the page doesn't reset the count)
const freeClicksUsed = typeof window !== 'undefined' ? ref(parseInt(sessionStorage.getItem('shiver_free_clicks') || '0')) : null;


// Generic checker function
const checkAuth = (actionCallback) => {
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
  
  if (token) {
    // User is logged in, run the requested action
    actionCallback();
  } else {
    // User is NOT logged in, open the modal
    requireLogin();
  }
};


// Drag features
const isDragCooldown = ref(false);
const draggingState = ref({
  active: false,
  point: null,
  offsetLat: 0,
  offsetLon: 0,
  startLat: 0, 
  startLon: 0
});

// Chart
const xAxisMin = ref('');
const xAxisMax = ref('');
const yAxisMin = ref('');
const yAxisMax = ref('');

// Vectors
const REFERENCE_VELOCITY = computed(() => {
  if (currentRegion.value === 'Greenland') {
    return 500; // Greenland Legend shows 250 m/yr
  } else {
    return 500; // Antarctica Legend shows 500 m/yr (since scale is 5000 vs 2250)
  }
});
const TILE_SIZE = 256; 
const vectorScaleLabel = computed(() => { return `${REFERENCE_VELOCITY.value} m/yr`; });
const arrowPixelWidth = computed(() => {
  if (!currentRegion.value) return 50; 

  // Backend Scales: Greenland=2250, Antarctica=5000
  const scale = currentRegion.value === 'Greenland' ? 5000 : 5000;
  
  // Math: (1000 / Scale) * 256
  // Greenland result: ~113px
  // Antarctica result: ~51px
  return (REFERENCE_VELOCITY.value / scale) * TILE_SIZE;
});

// --- ADVANCED OPTIONS ---
const showAdvanced = ref(false);

// 1. Define Defaults (Single Source of Truth)
const DEFAULTS = {
  buffer: 500,
  variable: ['speed'],
  smoothing: { gap: 24, win_raw: 1, win_daily: 25, poly: 2 }
};

// 2. State Definitions 
const availableVariable = ['speed', 'vx', 'vy'];
const VARIABLE_LABELS = { 
  speed: 'Speed', 
  vx: 'Easting velocity', 
  vy: 'Northing velocity' 
};
const currentPlotVariable = ref(DEFAULTS.variable[0] || 'speed'); 
const pendingBuffer = ref(DEFAULTS.buffer); 
const pendingVariable = ref([...DEFAULTS.variable]); 
const pendingSmoothingParams = ref({ ...DEFAULTS.smoothing });

// 3. Restore Defaults
// This now updates the "pending" values, so the UI in the popup actually resets.
const restoreDefaults = () => {
    // 1. Reset the base plot parameters
    pendingVariable.value = [...DEFAULTS.variable];
    pendingSmoothingParams.value = { ...DEFAULTS.smoothing };
    pendingBuffer.value = DEFAULTS.buffer;
    
    // Functionally identical to 'selectAllSources' – grab all available 
    // sources for the currently viewed region and re-check all their boxes.
    if (availableSources.value) {
        pendingSources.value = [...availableSources.value];
    }
};


// --- WATCHER FOR STATUS MESSAGE --- //
watch(statusMessage, (newVal) => {
  // 1. Clear any existing timer so we don't fade out prematurely
  if (messageTimeout) clearTimeout(messageTimeout);

  // 2. If message is cleared externally, do nothing
  if (!newVal) return;

  // 3. Logic: If it looks like a "completion" message, set a timer to hide it.
  //    If it looks like a "processing" message (ends in '...'), keep it visible.
  if (!newVal.endsWith('...')) {
      isMessageSpinnerRequired.value = false; // Stop spinner
      
      // Auto-hide after 2.5 seconds
      messageTimeout = setTimeout(() => {
          statusMessage.value = "";
      }, 2500);
  } else {
      isMessageSpinnerRequired.value = true; // Start spinner
  }
});


const getSiteLabel = (point, index) => {
  // 1. Try Metadata Name (from Shapefile/Zarr) -> User Name -> Generic ID
  // Use optional chaining (?.) because point.data might be loading
  const meta = point.data?.meta || {};
  let name = meta.site_name || point.name || `Site_${point.id}`;
  // 2. If it is a generic name (e.g. Site_0, Site_99), force it to be sequential (Site_1, Site_2)
  if (/^Site_\d+$/.test(name)) {
    return `Site_${index + 1}`;
  }
  // 3. Otherwise return the custom name (e.g. "Jakobshavn")
  return name;
};

// Define date formatter for plot relayout
const formatChartDate = (val) => {
  if (!val) return '';
  
  // Create a date object. Plotly dates are usually ISO strings or numbers.
  const d = new Date(val);
  
  // Check if the date is valid
  if (isNaN(d.getTime())) return '';

  // Format as YYYY-MM-DD
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
};

// --- FUNCTION 1: HANDLE CHART ZOOM (Chart updates Text Boxes) ---
const onPlotRelayout = (event) => {
  // 1. Check if this is an Auto-Range event (Double click or Reset)
  if (event['xaxis.autorange'] || event['yaxis.autorange']) {
      isUserZoomed.value = false; // UNLOCK
      // Clear variables logic (optional here as resetAxes handles it, but good for safety)
      if (event['xaxis.autorange']) { xAxisMin.value = ''; xAxisMax.value = ''; }
      if (event['yaxis.autorange']) { yAxisMin.value = ''; yAxisMax.value = ''; }
  } 
  // 2. Check if this is a Zoom event (User dragged box or axes)
  else if (event['xaxis.range[0]'] || event['yaxis.range[0]']) {
      isUserZoomed.value = true; // LOCK
      
      // Update X-Axis Variables
      if (event['xaxis.range[0]']) {
        xAxisMin.value = formatChartDate(event['xaxis.range[0]']);
        xAxisMax.value = formatChartDate(event['xaxis.range[1]']);
      }
      
      // Update Y-Axis Variables
      if (event['yaxis.range[0]']) {
        yAxisMin.value = Math.round(event['yaxis.range[0]'] * 100) / 100;
        yAxisMax.value = Math.round(event['yaxis.range[1]'] * 100) / 100;
      }
  }
};

// --- FUNCTION 2: HANDLE USER INPUT (Text Boxes update Chart) ---
const updatePlotAxes = () => {
  const graphDiv = document.getElementById('velocity-chart');
  if (!graphDiv) return;

  const update = {};
  isUserZoomed.value = true; // LOCK

  if (xAxisMin.value && xAxisMax.value) {
    update['xaxis.range'] = [xAxisMin.value, xAxisMax.value];
    update['xaxis.autorange'] = false;
  }

  if (yAxisMin.value !== '' && yAxisMax.value !== '') {
    update['yaxis.range'] = [parseFloat(yAxisMin.value), parseFloat(yAxisMax.value)];
    update['yaxis.autorange'] = false;
  }

  //Plotly.relayout(graphDiv, update);
  plotlyLib.value?.relayout(graphDiv, update);
};

// --- FUNCTION 3: RESET BUTTON ---
const resetAxes = () => {
  const graphDiv = document.getElementById('velocity-chart');
  if (!graphDiv) return;

  isUserZoomed.value = false; // UNLOCK
  xAxisMin.value = ''; xAxisMax.value = '';
  yAxisMin.value = ''; yAxisMax.value = '';

  plotlyLib.value?.relayout(graphDiv, {
    'xaxis.autorange': true,
    'yaxis.autorange': true
  });
};

// Function to calculate square bounds from a center point and buffer in meters
const getSquareBounds = (lat, lon, bufferMeters) => {
  // If buffer is 0, return the point itself (rectangle will be invisible)
  if (!bufferMeters || bufferMeters <= 0) return [[lat, lon], [lat, lon]];

  // Earth's radius approx calculation
  // 1 degree latitude is approx 111,111 meters
  const metersPerDegreeLat = 111111;
  
  // 1 degree longitude depends on latitude
  // Formula: 111,111 * cos(lat in radians)
  const metersPerDegreeLon = 111111 * Math.cos(lat * (Math.PI / 180));

  const deltaLat = bufferMeters / metersPerDegreeLat;
  const deltaLon = bufferMeters / metersPerDegreeLon;

  return [
    [lat - deltaLat, lon - deltaLon], // South-West corner
    [lat + deltaLat, lon + deltaLon]  // North-East corner
  ];
};

// --- Drag Logic ---
const startDrag = (e) => {
  if (e.cancelable) e.preventDefault();
  isDragging.value = true;
  // Change the cursor for the whole body so it doesn't flicker if you drag fast
  document.body.style.cursor = 'row-resize';
  // Prevent text selection highlighting while dragging
  document.body.style.userSelect = 'none';
  // Attach listeners to window so dragging continues even if mouse leaves the handle
  window.addEventListener('mousemove', onDrag);
  window.addEventListener('mouseup', stopDrag);
  // Attach Touch Listeners (passive: false allows us to prevent scrolling)
  window.addEventListener('touchmove', onDrag, { passive: false });
  window.addEventListener('touchend', stopDrag);
};

const onDrag = (e) => {
  if (!isDragging.value) return;
  
  // 1. Get Client Y (Unified for Mouse & Touch)
  let currentY; 
  if (e.type.includes('touch')) {
      // Touch Event: clientY is nested inside touches[0]
      currentY = e.touches[0].clientY;
      
      // Prevent scrolling the page while dragging
      if (e.cancelable) e.preventDefault(); 
  } else {
      // Mouse Event: clientY is on the root event
      currentY = e.clientY;
  }

  const container = document.querySelector('.page-container');
  if (!container) return;

  // 2. Calculate position relative to container
  const containerRect = container.getBoundingClientRect();
  const relativeY = currentY - containerRect.top;
  
  // Convert to percentage
  let newHeight = (relativeY / containerRect.height) * 100;

  // Clamp limits (e.g., Map can't be smaller than 10% or larger than 90%)
  newHeight = Math.min(Math.max(newHeight, 10), 90);
  mapHeightPercent.value = newHeight;

  // Trigger redraw of plotly and leaflet
  window.dispatchEvent(new Event('resize'));
};

const stopDrag = () => {
  isDragging.value = false;
  // Revert cursor and text selection to default
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
  // Remove Mouse Listeners
  window.removeEventListener('mousemove', onDrag);
  window.removeEventListener('mouseup', stopDrag);
  // Remove Touch Listeners
  window.removeEventListener('touchmove', onDrag);
  window.removeEventListener('touchend', stopDrag);
  // Final resize trigger to ensure crisp rendering
  setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
};

// Determine colour based on number of points
const distributeColors = () => {
  const n = selectedPoints.value.length;
  if (n === 0) return;

  // Map to a NEW array to ensure Vue detects the change deeply
  selectedPoints.value = selectedPoints.value.map((point, index) => {
    let newColor;
    if (n === 1) {
      newColor = COLORS[0];
    } else {
      const maxIndex = COLORS.length - 1;
      const colorIndex = Math.round(index * (maxIndex / (n - 1)));
      newColor = COLORS[colorIndex];
    }
    // Return a copy of the point with the new color
    return { ...point, color: newColor };
  });
};

// Add a timer variable outside the watch
let colorDebounceTimer;
// Watch to keep things in sync
watch(() => selectedPoints.value.length, () => {
  // 1. Immediate Update (Keeps it responsive)
  distributeColors();
  if (typeof updateChart === 'function') updateChart();

  // 2. "Cleanup" Update (The Fix)
  // This waits 200ms after the last change and forces one final color check.
  // This often fixes the "stuck on the last color" bug.
  clearTimeout(colorDebounceTimer);
  colorDebounceTimer = setTimeout(() => {
    distributeColors(); 
  }, 200);
});

// Generate suffix string for filenames: e.g. _gf24_wr25_wd25_p2
const smoothingSuffix = computed(() => {
    const p = pendingSmoothingParams.value; 
    if (!p) return ''; 
    return `_gf${p.gap}_wr${p.win_raw}_wd${p.win_daily}_p${p.poly}`;
});

// Computed list of available plots based on USER SELECTION
const plotOptions = computed(() => {
  return pendingVariable.value.map(v => ({
    val: v,
    label: VARIABLE_LABELS[v] || v
  }));
});

// Ensure currentPlotVariable is valid; if not, reset
watch(plotOptions, (newOpts) => {
  // Edge case: User unchecked all variables
  if (newOpts.length === 0) {
    currentPlotVariable.value = null;
    updateChart(); 
    return;
  }

  // Check if the currently selected plot variable is still in the options array
  const isValid = newOpts.some(opt => opt.val === currentPlotVariable.value);

  // If it's no longer valid (user unchecked it), fallback to the first available option
  if (!isValid) {
    currentPlotVariable.value = newOpts[0].val;
    updateChart();
  }
});

// Dynamic label for the download button
const xlsxDownloadLabel = computed(() => selectedPoints.value.length > 1 ? 'Download all data (.zip)' : 'Download data (.xlsx)');
const chartDownloadLabel = computed(() => plotOptions.value.length > 1 ? 'Download all graphs (.zip)' : 'Download graph (.png)' );

// --- COMPUTED URLs FOR TILES ---
// "timestamp" is used as a query parameter (?t=...) to force the browser 
// to re-fetch tiles if the data changes, avoiding stale cache issues.
const timestamp = computed(() => Date.now()); 

// Note: Leaflet <img/> tags don't use axios, so we must construct the full URL string manually.
// We remove any trailing slash from API_URL to avoid double slashes like '...8000//api...'
const baseUrl = API_URL.replace(/\/$/, '');
const wmsOverlayUrl = computed(() => `${baseUrl}/api/wms/${currentRegion.value}?t=${timestamp.value}`);
const wmsLandsatUrl = computed(() => `${baseUrl}/api/wms/${currentRegion.value}?t=${timestamp.value}`);
const wmsVectorUrl = computed(() => `${baseUrl}/api/wms/${currentRegion.value}/vectors`);

//const speedUrl = computed(() => `${baseUrl}/api/tiles/${currentRegion.value}/speed/{z}/{x}/{y}.png?t=${timestamp.value}`);
//const countUrl = computed(() => `${baseUrl}/api/tiles/${currentRegion.value}/count/{z}/{x}/{y}.png?t=${timestamp.value}`);
//const trendUrl = computed(() => `${baseUrl}/api/tiles/${currentRegion.value}/trend/{z}/{x}/{y}.png?t=${timestamp.value}`);
//const vectorUrl = computed(() => `${baseUrl}/api/tiles/${currentRegion.value}/vectors/{z}/{x}/{y}.png?t=${timestamp.value}` );
//const hillshadeUrl = computed(() => `${baseUrl}/api/tiles/${currentRegion.value}/hillshade/{z}/{x}/{y}.png?t=${timestamp.value}` );

// --- LEGEND & LAYER LOGIC ---
// Leaflet's <l-control-layers> handles the actual map toggling.
// These events listen to Leaflet to update our local 'overlayLayer' state,
// which determines which Legend bar to show in the bottom right.
const iceEdgeStyle = { color: "black", weight: 2 };
const groundingLineStyle = { color: "magenta", weight: 2 };

// FETCH MARGIN DATA ---
const loadMarginData = async () => {
  statusMessage.value = "Loading margin data...";
  try {
    // Load both files in parallel
    const [edgeRes, groundRes] = await Promise.all([
      apiClient.get('/static/iceedge_merged_simple.geojson'),
      apiClient.get('/static/apgroundingline_simple.geojson')
    ]);
    
    iceEdgeData.value = edgeRes.data;
    groundingLineData.value = groundRes.data;
    statusMessage.value = "Margin data loaded.";
  } catch (e) {
    console.error(e);
    statusMessage.value = "Error loading margins.";
  }
};

// Max speed label changes between Greenland (400) and Antarctica (800)
const maxTrendLabel = computed(() => currentRegion.value === 'Greenland' ? '2.5' : '15');
const minTrendLabel = computed(() => currentRegion.value === 'Greenland' ? '-2.5' : '-15');
const maxCountLabel = computed(() => currentRegion.value === 'Greenland' ? '750' : '200');

// --- REGION MANAGEMENT ---
const switchRegion = (updateUrl = true) => {
  clearAll(); 
  
  if (currentRegion.value === 'Greenland') {
    center.value = [71.394,-40.987]; zoom.value = 1; 
  } else {
    center.value = [-87.82, 87.09]; zoom.value = 0; 
  }
  
  // Force Leaflet to fly to the new center (safe here because map is mounted)
  if (map.value && map.value.leafletObject) {
      map.value.leafletObject.setView(center.value, zoom.value);
  }
  
  if (updateUrl) {
    syncUrl();
  }
};

// --- DATA FETCHING & BUFFER LOGIC ---
let debounceTimer = null;
const debouncedRefetch = () => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { refetchAllPoints(); }, 600);
};


const applyAdvancedOptions = async () => {
  // 1. Validation 
  if (pendingSources.value.length === 0 || pendingVariable.value.length === 0) {
      alert("Warning: Please select at least one Data Source and one variable.");
      return;
  }

  // 2. Define the "Target" Settings
  const targetSettings = {
      sources: [...pendingSources.value],
      buffer: pendingBuffer.value,
      variable: pendingVariable.value,
      smoothing: pendingSmoothingParams.value
  };

  // 3. SMART CHECK: Do we *need* to fetch?
  const needsFetch = selectedPoints.value.some(point => {
      // Fallback to empty object if settings are missing for some reason
      const current = point.settings || {}; 

      // A. Fundamental Parameters Changed? (Store, Buffer, or Smoothing)
      if (current.buffer !== targetSettings.buffer) return true;
      if (JSON.stringify(current.smoothing) !== JSON.stringify(targetSettings.smoothing)) return true;

	  // B. Multi-Source Check: Did the user add or remove a data source?
	  const missingSource = targetSettings.sources.some(s => !(current.sources || []).includes(s));
	  if (missingSource) return true;
	  const removedSource = (current.sources || []).some(s => !targetSettings.sources.includes(s));
	  if (removedSource) return true;
	  const missingVariable = targetSettings.variable.some(v => !(current.variable || []).includes(v));
	  if (missingVariable) return true;

      return false; // Point is compatible (it's a superset or exact match)
  });

  // 4. EXECUTE
  if (needsFetch) {
      // Scenario 1: Something fundamental changed or data is missing.
      // We must fetch fresh data for everyone to ensure consistency.
      await refetchAllPoints();
  } else {
      // Scenario 2: Optimization! 
      // We are only REMOVING variables or keeping things same.
      // No server call needed. Just update the settings objects locally.
      selectedPoints.value.forEach(point => {
          // Update the settings "metadata" so the chart knows to hide the removed variable
          point.settings = JSON.parse(JSON.stringify(targetSettings));
          point.buffer = targetSettings.buffer;
      });
      
      // Force chart redraw
      updateChart();
      statusMessage.value = "Updated (No fetch needed).";
  }
  
  // Close the modal (optional)
  // showAdvanced.value = false; 
};


// Refetch data for ALL points with the new buffer size and/or new filtering option
const refetchAllPoints = async () => {
  if (selectedPoints.value.length === 0) return;

  isRefreshing.value = true;
  statusMessage.value = "Updating all points...";

  // 1. Prepare the Global Settings (The "New" State)
  const useSources = [...pendingSources.value];
  const useBuffer = pendingBuffer.value;
  const useVariable = pendingVariable.value;     
  const useSmoothing = { ...pendingSmoothingParams.value }; 
  
  // Define newSettings ---
  // We package these together so we can save them into the point later
  const newSettings = {
    sources: useSources,
    buffer: useBuffer,
    variable: useVariable,
    smoothing: useSmoothing
  };

  // 2. Prepare ROIs (List of [lat, lon])
  const roiList = selectedPoints.value.map(p => [p.lat, p.lon]);

  trackEvent("data_refresh", {
    event_category: "interaction",
    event_label: "batch_refresh",
    count: roiList.length,
    buffer: useBuffer
  });

  try {
    // 3. Create ONE Payload for ALL points
    const payload = {
      roi: roiList, 
      buffer: useBuffer,
      variable: useVariable,
      gap_fill: useSmoothing.gap,
      win_raw: useSmoothing.win_raw,
      win_daily: useSmoothing.win_daily,
      poly: useSmoothing.poly
    };
	
	// Auth header injection
	const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
    const config = {};
    if (token) {
        config.headers = { Authorization: `Bearer ${token}` };
    }

    // 4. Set payload extras
	payload.sources = useSources;
	payload.variable = useVariable; 
	
      // 5. Single Batch Request
      const response = await apiClient.post('/api/timeseries/multi/json', payload);
      const responseData = response.data;

    // 5. Map Response back to Points
    // If responseData is an Array:
    const resultsArray = Array.isArray(responseData) 
        ? responseData 
        : Object.values(responseData); // Convert object values to array to guarantee order

    selectedPoints.value.forEach((point, index) => {
        // Get the data corresponding to this point's position in the list
        const newData = resultsArray[index];

        if (newData) {
            // A. Update Raw Data
            point.data = newData;
            
            // B. UPDATE SETTINGS (Deep Copy)
            // Detach this point's settings from the UI state completely
            point.settings = JSON.parse(JSON.stringify(newSettings));
            
            // Sync top-level convenience prop
            point.buffer = newSettings.buffer;
            
            console.log(`Successfully updated point ${index + 1}`);
        } else {
            console.warn(`No data returned for point at index ${index} (ID: ${point.id})`);
        }
    });

    statusMessage.value = "All points updated.";
    updateChart();

  } catch (error) {
    console.error("Batch update failed:", error);
    statusMessage.value = "Error updating data.";
  } finally {
    isRefreshing.value = false;
  }
};

// --- MAP INTERACTION ---
const onMapClick = async (e) => {
  // 1. Validation Checks 
  if (draggingState.value.active || isDragCooldown.value) return;
  const target = e.originalEvent?.target;
  if (!target || !target.isConnected) return;
  if (target.closest('.leaflet-control-container') || target.closest('.leaflet-control')) return;
  if (!map.value) return;
  
  if (selectedPoints.value.length >= 10) {
    alert("Maximum of 10 points allowed.");
    return;
  }
  
  // Validation: Ensure user hasn't deselected required menu items
  if (pendingSources.value.length === 0 || pendingVariable.value.length === 0) {
	  alert("Warning: Please select at least one Data Source and variable.");
	  return;
  }
  
  // Check free tier limit
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null; // Check if logged in
  if (!token) {
      // If they have already hit the limit
      if (freeClicksUsed.value >= MAX_FREE_CLICKS) {
          // Optional: Add a small delay or alert so they know WHY the modal is opening
          alert(`You have used your ${MAX_FREE_CLICKS} free data inspections. Please log in to continue.`);
          requireLogin(); // Open the App.vue Login Modal
          return; // STOP HERE
      }
      // Otherwise, count this click
      freeClicksUsed.value++;
	  if (typeof window !== 'undefined') {
          sessionStorage.setItem('shiver_free_clicks', freeClicksUsed.value);
      }
      console.log(`Free clicks used: ${freeClicksUsed.value}/${MAX_FREE_CLICKS}`);
  }
  
  // 2. PREPARE SETTINGS SNAPSHOT
  // Instead of updating global state, we create a specific settings object 
  // for THIS new point based on the current menu state.
  const newPointSettings = {
      sources: [...pendingSources.value],
      buffer: pendingBuffer.value,
      variable: [...pendingVariable.value],
      smoothing: { ...pendingSmoothingParams.value }
  };
  
  // 3. Track clicks
  trackEvent("map_click", {
    event_category: "interaction",
    event_label: "extract_timeseries",
    region: currentRegion.value,
    lat: e.latlng.lat.toFixed(4),
    lon: e.latlng.lng.toFixed(4),
    buffer: newPointSettings.buffer
  });
    
  const newId = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    
  // 5. FETCH
  // We pass 'newPointSettings' as the 5th argument so the point is created 
  // with these specific options.
  await fetchSinglePoint(
      newId, 
      e.latlng.lat, 
      e.latlng.lng, 
      COLORS[0], // Temporary color (distributeColors will fix it)
      newPointSettings
  );
  
  // Format the new point to e.g., "53.38,-1.47" to keep URLs relatively clean
  syncUrl();
};


// Whenever points are added or removed, fix colors and update chart automatically.
watch(() => selectedPoints.value.length, () => {
  distributeColors();
  if (typeof updateChart === 'function') {
    updateChart();
  }
});


// --- GLACIER BASINS --- //
// Keep track of the actual Leaflet layer so we can remove it later
let currentBasinLayer = null; 

// 1. Define the available basins for each region
const REGION_BASINS = {
    'Antarctica': [
        { id: 'none', label: 'No Basins', url: null },
        { id: 'ap_basins', label: 'Peninsula basins', url: '/static/apbasinoutlines.geojson' },
        { id: 'ant_set2', label: 'Glacier basins', url: '/static/AntarcticBasins.geojson' }, 
        { id: 'ant_set3', label: 'IMBIE basins', url: '/static/AntarcticBasinsIMBIE.geojson' }  
    ],
    'Greenland': [
        { id: 'none', label: 'No Basins', url: null },
        { id: 'gr_set1', label: 'Mouginot basins', url: '/static/GreenlandBasinsMouginot.geojson' }, 
		{ id: 'gr_set2', label: 'Mankoff basins', url: '/static/GreenlandBasinsMankoff.geojson' }, 
		{ id: 'gr_set3', label: 'IMBIE basins', url: '/static/GreenlandBasinsIMBIE.geojson' } 
    ]
};

// 2. Define the defaults for each region
const DEFAULT_BASINS = {
    'Antarctica': 'ant_set3',
    'Greenland': 'gr_set3'
};

// Computed list of basins for the current region
const availableBasins = computed(() => {
    const region = currentRegion.value || 'Greenland';
    return REGION_BASINS[region] || [];
});

// 3. Initialize with the default for the starting region
const selectedBasinId = ref(DEFAULT_BASINS[currentRegion.value || 'Greenland'] || 'none');

// 4. This will hold the actual loaded JSON data for the template
const currentBasinData = ref(null);

// 5. Watch for Region Changes -> Reset to that region's default
watch(currentRegion, (newRegion) => {
    selectedBasinId.value = DEFAULT_BASINS[newRegion] || 'none';
});

// 6. Watch for Basin ID Changes -> Fetch the data
watch(selectedBasinId, async (newId) => {
    if (newId === 'none') {
        currentBasinData.value = null; // Clears the map
        return;
    }

    const basinObj = availableBasins.value.find(b => b.id === newId);
    if (!basinObj || !basinObj.url) return;

    try {
        const response = await apiClient.get(basinObj.url);        
        // Update the reactive variable, which feeds the <l-geo-json> component
        currentBasinData.value = response.data;
    } catch (error) {
        console.error("Failed to load basin geojson:", error);
        currentBasinData.value = null;
    }
}, { immediate: true }); // The { immediate: true } forces this to run once on page load!

// 7. Style for the glacier polygons (invisible fill, black outline #000000)
const outlineStyle = () => {
  return {
    color: "#708090",
    weight: 1,
    fillOpacity: 0,
    className: 'basin-polygon'  
  };
};


// --- GLACIER LABELS --- //
const glacierNamesData = ref(null);

// 1. Load peninsula names
const loadGlacierNames = async () => {
  if (glacierNamesData.value) return; 
  try {
    const response = await apiClient.get('/static/apc_glaciers_wkt.geojson');
    glacierNamesData.value = response.data;
  } catch (e) {
    console.error("Failed to load glacier names:", e);
  }
};

// 2. Fetch the Peninsula names when viewing Antarctica
watch(currentRegion, (newRegion) => {
    selectedBasinId.value = DEFAULT_BASINS[newRegion] || 'none';
    if (newRegion === 'Antarctica') {
        loadGlacierNames();
    }
}, { immediate: true });

// 3. Define naming options
const glacierLabelOptions = {
  // Render invisible circle markers so we don't see blue pins
  pointToLayer: (feature, latlng) => {
    return L.value.circleMarker(latlng, { radius: 0, opacity: 0, fillOpacity: 0 });
  },
  // Bind the permanent tooltip using the 'feature' property from your new file
  onEachFeature: (feature, layer) => {
    if (feature.properties && feature.properties.feature) {
      layer.bindTooltip(feature.properties.feature, {
        permanent: true,
        direction: 'center',
        className: 'glacier-name-tooltip'
      });
    }
  }
};

// 4. Set options for the all basins - this  version displays all names at once
//const basinOptions = {
//    onEachFeature: (feature, layer) => {
//        if (feature.properties && feature.properties.NAME) {
//            layer.bindTooltip(feature.properties.NAME, {
//                permanent: true,
//                direction: 'center',
//                className: 'basin-name-tooltip' 
//            });
//        }
//
//    }
//};

// 4. Set options for the all basins - this version displays names on hover and all basin datasets the same
//const basinOptions = {
//    onEachFeature: (feature, layer) => {
//        if (feature.properties && feature.properties.NAME) {
//            // sticky: true makes it follow the cursor on hover!
//            // We remove permanent: true so it hides when not hovering.
//            layer.bindTooltip(feature.properties.NAME, {
//                sticky: true,
//				offset: [20, -20],
//                className: 'basin-hover-tooltip' 
//            });
//        }
//    }
//};

// 4. Set options for all basins dynamically
const basinOptions = {
    onEachFeature: (feature, layer) => {
        if (feature.properties && feature.properties.NAME) {
            
            // Check the active dataset INSIDE the Leaflet loop!
            const isImbie = selectedBasinId.value === 'ant_set3' || selectedBasinId.value === 'gr_set3';
            
            if (isImbie) {
                // IMBIE BASINS: Permanent tooltips at all times
                layer.bindTooltip(feature.properties.NAME, {
                    permanent: true,
                    direction: 'center',
                    className: 'imbie-basin-tooltip'
                });
            } else {
                // OTHER BASINS: Hover tooltips
                layer.bindTooltip(feature.properties.NAME, {
                    sticky: true,
                    offset: [20, -20],
                    className: 'basin-hover-tooltip' 
                });
            }
        }
    }
};


// --- FILE UPLOAD ---
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // Track uploads
  trackEvent("timeseries_file_upload", {
    event_category: "interaction",
    event_label: "timeseries_file_upload",
    region: currentRegion.value,
  });
  
  // 1. Validation 
  if (pendingSources.value.length === 0 || pendingVariable.value.length === 0) {
	  alert("Warning: Please select at least one Data Source and variable before uploading.");
	  event.target.value = '';
	  return;
  }

  // 2. Prepare Settings Snapshot (Crucial for chart to work!)
  const uploadSettings = {
      sources: [...pendingSources.value],
      buffer: pendingBuffer.value,
      variable: [...pendingVariable.value],       
      smoothing: { ...pendingSmoothingParams.value } 
  };

  isUploading.value = true;
  statusMessage.value = "Uploading...";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("buffer", uploadSettings.buffer);
  
  // Append multi-source arrays
  uploadSettings.sources.forEach(s => formData.append("sources", s));
  uploadSettings.variable.forEach(v => formData.append("variable", v));
  
  // Append smoothing
  formData.append("gap_fill", uploadSettings.smoothing.gap);
  formData.append("win_raw", uploadSettings.smoothing.win_raw);
  formData.append("win_daily", uploadSettings.smoothing.win_daily);
  formData.append("poly", uploadSettings.smoothing.poly);
  
  // 1. Prepare Headers
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
  const config = { headers: {} };

    if (token) {
	    config.headers['Authorization'] = `Bearer ${token}`;
    }

  try {
  
	// ping backend
	const response = await axios.post(`${API_URL}/api/timeseries/multi/upload`, formData, config);
	
	// read results
    const results = response.data;
    if (results.status === 'error') throw new Error(results.message);

    // 3. Process results (Fast Loop)
    const entries = Object.entries(results);
    let addedCount = 0;

    // We can use a simple loop without 'await' for speed
    for (const [siteName, data] of entries) {
        // Stop if we hit the limit
        if (selectedPoints.value.length >= 10) break;

        const ptLat = data.meta?.lat || 0;
        const ptLon = data.meta?.lon || 0;
        
        // Handle buffer logic
        const metaBuffer = data.meta?.buffer_used;
        const siteSpecificBuffer = (metaBuffer !== undefined && metaBuffer !== null) 
            ? Number(metaBuffer) 
            : Number(pendingBuffer.value);

        const color = COLORS[selectedPoints.value.length % COLORS.length];

        // Create and push the point
        selectedPoints.value.push({
            id: Date.now() + addedCount, // Ensure unique IDs
            lat: ptLat,
            lon: ptLon,
            color: color,
            data: data,
            name: siteName,
            buffer: siteSpecificBuffer,
            settings: JSON.parse(JSON.stringify(uploadSettings)) // Deep copy settings
        });

        addedCount++;
    }

    statusMessage.value = `Loaded ${addedCount} sites.`;
    updateChart();
    event.target.value = ''; // Reset file input
	
	if (addedCount > 0) {
      syncUrl();
    }

  } catch (error) {
    console.error(error);
    statusMessage.value = "Upload failed.";
    alert("Upload failed: " + (error.message || "Unknown error"));
  } finally {
    isUploading.value = false;
  }
};


// Fetch data for a single point (used by Map Click)
const fetchSinglePoint = async (id, lat, lon, color, customSettings = null) => {
  isFetching.value = true;
  statusMessage.value = "Fetching...";
  
  // BEHAVIOUR 1 LOGIC:
  // If customSettings is null (New Point Click), snapshot the current Advanced Options.
  // If customSettings exists (Refresh or Mass Update), use those.
  const settings = customSettings || {
      sources: [...pendingSources.value],
      buffer: pendingBuffer.value,
      variable: [...pendingVariable.value],
      smoothing: { ...pendingSmoothingParams.value }
  };
  
  // Track data fetching
  trackEvent("data_fetch", {
	  event_category: "interaction",
	  event_label: "data_fetch",
	  buffer: settings.buffer,
      variable: settings.variable,
      quality: "raw",
      region: currentRegion.value,
	  lat: lat,
	  lon: lon
	});
  
  // Ping the backend
  try {
    const payload = { 
        roi: [[lat, lon]], 
        buffer: settings.buffer,
        variable: settings.variable, 
        gap_fill: settings.smoothing.gap,
        win_raw: settings.smoothing.win_raw,
        win_daily: settings.smoothing.win_daily,
        poly: settings.smoothing.poly,
		sources: settings.sources
    };
	
	// 2. Prepare Headers (CORRECT WAY)
	const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
	const config = { headers: {} };
	if (token) config.headers['Authorization'] = `Bearer ${token}`; 
  
	// Request 
    const response = await apiClient.post('/api/timeseries/multi/json', payload, config);
    const rawData = response.data;
    const firstKey = Object.keys(rawData)[0];
    const siteData = rawData[firstKey];
	
	// Check for ping errors
    if (siteData.status === 'error') {
      statusMessage.value = `Error: ${siteData.message}`; return;
    }
	
	// Save the snapshot
    // We store 'settings' inside the point. This freezes the configuration 
    // for this specific point until the user explicitly changes it.
    const newPoint = { id, lat, lon, color, settings: settings, buffer: settings.buffer, data: siteData, name: firstKey };
	
	// Record
    const idx = selectedPoints.value.findIndex(p => p.id === id);
    if (idx >= 0) selectedPoints.value[idx] = newPoint;
    else selectedPoints.value.push(newPoint);
	
	// Show status
    statusMessage.value = "Loaded.";
    updateChart();
  } catch (error) {
    console.error(error); statusMessage.value = "Server Error.";
  } finally {
    isFetching.value = false;
  }
};

// Wrapper for updating a point when coords are manually edited
const refreshPointData = async (point) => {
    // Construct settings using the point's existing variables/smoothing
    // but the new buffer from the input box.
    const updatedSettings = {
        ...point.settings, // Copy old variable, smoothing
        buffer: point.buffer // Use the new buffer value
    };
    
    // Pass these settings back to fetchSinglePoint
    await fetchSinglePoint(point.id, point.lat, point.lon, point.color, updatedSettings);
};
const removePoint = (id) => { selectedPoints.value = selectedPoints.value.filter(p => p.id !== id); distributeColors(); updateChart(); };
const clearAll = () => { 
  // 1. Clear component UI state
  selectedPoints.value = []; 
  
  if (typeof plotlyLib.value !== 'undefined' && plotlyLib.value?.purge) {
    plotlyLib.value?.purge('velocity-chart'); 
  }
  
  // 2. Clean the URL (keep the region context, but drop the points 'p')
  router.replace({
    path: route.path,
    query: { reg: currentRegion.value }
  });
};



// --- CHART PLOTTING (PLOTLY) ---
// Dynamically get today's date in local YYYY-MM-DD format
const maxChartDate = computed(() => {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
  const dd = String(today.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
});

// Set a static hard floor for how far back they can look
const minChartDate = '1950-01-01';

// BUILD CHART DATA (Returns {data, layout})
const buildChartConfig = (plotKey) => {
  const traces = [];
  const renderedSources = new Set();
  
  // Track min/max to tightly bind the axes to valid data only
  let globalMinX = null;
  let globalMaxX = null;
  let globalMinY = Infinity;
  let globalMaxY = -Infinity;
  
  // Reset Legend Items
  legendItems.value = [];

  selectedPoints.value.forEach((point, idx) => {
    // A. DATA EXISTENCE CHECK
    if (point.data?.status === 'error' || !point.data?.data) return;
    
    const settings = point.settings || { variable: [] };
    const rootData = point.data.data;
    
    // B. SETTINGS CHECK & DATA MAPPING
    // Ensure this variable was selected in point settings and exists in payload
    const isEnabled = Array.isArray(settings.variable) && settings.variable.includes(plotKey); 
    if (!isEnabled || !rootData[plotKey]) return;

    const varData = rootData[plotKey]; // Contains { raw: [], smoothed: [] }
    const activeErrorArray = rootData[`${plotKey}_error`] || rootData.speed_error || [];

    // Setup styles
    const pale = makePale(point.color);
    const label = /^Site_\d+$/.test(point.name) ? `Site${idx + 1}` : point.name;
    const isVisible = point.visible !== false;
    
    // --- PREPARE HOVER DATA ---
    const customData = rootData.count.map((c, i) => [
      c, 
      rootData.dt ? rootData.dt[i] : null, 
      activeErrorArray ? activeErrorArray[i] : null,
      rootData.data_source ? rootData.data_source[i] : 'N/A'
    ]);
    
    // Dynamic Hover Template
    const hoverTemplate = 
      `<b>Date</b>: %{x|%Y-%m-%d}<br>` +
      `<b>Value</b>: %{y:.1f} &plusmn; %{customdata[2]:.1f} m/yr<br>` + 
      `<b>Pixels</b>: %{customdata[0]}<br>` +
      `<b>dt</b>: %{customdata[1]} days<br>` +
      `<b>Source</b>: %{customdata[3]}` +
      `<extra></extra>`;
    
    // --- COLOR BY SOURCE LOGIC ---
    if (colorBySource.value) {
      const sourceGroups = {};
      
      rootData.dates.forEach((dateStr, i) => {
        const rawValue = varData.raw[i];
        if (rawValue === null || rawValue === undefined || rawValue === 'NaN' || Number.isNaN(Number(rawValue))) return;
        
        // Track min and max
        const cTime = new Date(dateStr).getTime();
        if (globalMinX === null || cTime < globalMinX) globalMinX = cTime;
        if (globalMaxX === null || cTime > globalMaxX) globalMaxX = cTime;
        if (rawValue < globalMinY) globalMinY = rawValue;
        if (rawValue > globalMaxY) globalMaxY = rawValue;
        
        const source = rootData.data_source ? rootData.data_source[i] : 'Unknown';
        if (!sourceGroups[source]) {
          sourceGroups[source] = { x: [], y: [], dt: [], error: [], custom: [] };
        }
        
        sourceGroups[source].x.push(new Date(dateStr));
        sourceGroups[source].y.push(rawValue);
        sourceGroups[source].dt.push(rootData.dt && rootData.dt[i] !== null ? Number(rootData.dt[i]) : 0);
        sourceGroups[source].error.push(activeErrorArray ? activeErrorArray[i] : 0);
        sourceGroups[source].custom.push(customData[i]);
      });

      // Create segmented traces for each source
      Object.keys(sourceGroups).forEach(source => {
        const group = sourceGroups[source];
        const sColor = getSourceColor(source);
        const sPale = makePale(sColor);
        
        // 1. Horizontal Bars for dt range
        const hX = [], hY = [];
        group.x.forEach((dateObj, idx) => {
          const dtDays = group.dt[idx];
          if (dtDays > 0) {
            const cTime = dateObj.getTime();
            const halfMs = (dtDays / 2) * 86400000;
            hX.push(new Date(cTime - halfMs), new Date(cTime + halfMs), null);
            hY.push(group.y[idx], group.y[idx], null);
          }
        });

        traces.push({
          x: hX, y: hY, mode: 'lines', type: 'scatter', showlegend: false,
          hoverinfo: 'skip', legendgroup: source, visible: isVisible,
          line: { color: sPale, width: 2 }
        });

        // 2. Scatter / Vertical Error
        const isNewSourceInLegend = !renderedSources.has(source);
        if (isNewSourceInLegend) renderedSources.add(source);

        traces.push({
          x: group.x, y: group.y, mode: 'markers', type: 'scatter',
          name: source, 
          showlegend: isNewSourceInLegend,
          legendgroup: source, visible: isVisible,
          marker: { color: sPale, size: 5, line: { width: 1, color: sColor } },
          error_y: { type: 'data', array: group.speed_error, visible: true, color: sPale, thickness: 1, width: 0 },
          customdata: group.custom,
          hovertemplate: hoverTemplate
        });
      });

    } else {
      // --- COLOR BY SITE LOGIC ---
      const hBarX = [];
      const hBarY = [];

      rootData.dates.forEach((dateStr, i) => {
        const rawValue = varData.raw[i];
        const dtDays = rootData.dt ? rootData.dt[i] : 0;
        
        if (rawValue === null || rawValue === undefined || rawValue === 'NaN' || Number.isNaN(Number(rawValue))) return;
        
        const cTime = new Date(dateStr).getTime();
        if (globalMinX === null || cTime < globalMinX) globalMinX = cTime;
        if (globalMaxX === null || cTime > globalMaxX) globalMaxX = cTime;
        if (rawValue < globalMinY) globalMinY = rawValue;
        if (rawValue > globalMaxY) globalMaxY = rawValue;

        if (dtDays > 0) {
          const halfDtMs = (dtDays / 2) * 86400000; 
          hBarX.push(new Date(cTime - halfDtMs), new Date(cTime + halfDtMs), null);
          hBarY.push(rawValue, rawValue, null);
        }
      });

      traces.push({
        x: hBarX,
        y: hBarY,
        mode: 'lines',
        type: 'scatter',
        showlegend: false,
        visible: isVisible,
        legendgroup: `g${point.id}`,
        hoverinfo: 'skip', 
        line: { color: pale, width: 2 }
      });

      // Scatter / Vertical Error
      traces.push({
        x: rootData.dates.map(d => new Date(d)), 
        y: varData.raw, 
        mode: 'markers', 
        type: 'scatter', 
        name: label, 
        showlegend: false, 
        visible: isVisible,
        legendgroup: `g${point.id}`, 
        marker: { color: pale, size: 5, line: { width: 1, color: point.color } },
        error_y: { type: 'data', array: activeErrorArray, visible: true, color: pale, thickness: 1, width: 0 },
        customdata: customData,
        hovertemplate: hoverTemplate
      });
    }
    
    // --- TRACE 2: LINES (Smoothed) ---
    traces.push({
      x: rootData.dates.map(d => new Date(d)), 
      y: varData.smoothed, 
      mode: 'lines', 
      type: 'scatter', 
      name: label,
      showlegend: false,
      visible: isVisible,
      legendgroup: `g${point.id}`, 
      line: { color: point.color, width: 3 }
    });
    
    // --- TREND LINE LOGIC ---
    let trendText = null;
    if (showTrends.value && trendStart.value && trendEnd.value) {
      const tStart = new Date(trendStart.value).getTime();
      const tEnd = new Date(trendEnd.value).getTime();
      const filteredDates = [];
      const filteredVals = [];

      rootData.dates.forEach((d, i) => {
        const t = new Date(d).getTime();
        const val = varData.raw[i]; 
        if (t >= tStart && t <= tEnd && val !== null && val !== undefined) {
          filteredDates.push(d);
          filteredVals.push(val);
        }
      });

      const stats = calculateRegression(filteredDates, filteredVals);

      if (stats) {
        const x1 = tStart;
        const x2 = tEnd;
        const y1 = stats.slope * x1 + stats.intercept;
        const y2 = stats.slope * x2 + stats.intercept;
        
        const trendVal = stats.slopePerYear > 0 
          ? `+${stats.slopePerYear.toFixed(1)}` 
          : stats.slopePerYear.toFixed(1);

        let sig = 'ns';
        if (stats.pValue < 0.001) sig = '***';
        else if (stats.pValue < 0.01) sig = '**';
        else if (stats.pValue < 0.05) sig = '*';
        
        trendText = `${trendVal} m/yr<sup>2</sup> (${sig})`;

        traces.push({
          x: [trendStart.value, trendEnd.value],
          y: [y1, y2],
          mode: 'lines',
          type: 'scatter',
          legendgroup: `g${point.id}`,
          showlegend: false,
          visible: isVisible,
          line: { color: point.color, width: 2, dash: 'dash' },
          hoverinfo: 'skip' 
        });
      }
    }
    
    // --- POPULATE CUSTOM LEGEND ---
    legendItems.value.push({
      id: point.id,
      label: label,
      color: point.color,
      trendText: trendText,
      isVisible: isVisible
    });
  });
  
  // Define axis labels based on plotKey
  let yAxisLabel = "Velocity (m/yr)";
  if (plotKey === 'speed') yAxisLabel = "Speed (m/yr)"; 
  else if (plotKey === 'vx') yAxisLabel = "Easting velocity (m/yr)"; 
  else if (plotKey === 'vy') yAxisLabel = "Northing velocity (m/yr)";
  
  // Base64 SVG Watermark
  const watermarkSvg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="20" viewBox="0 0 100 20">
      <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" 
            font-family="sans-serif" font-weight="900" font-size="18" 
            fill="rgba(135, 206, 235, 0.15)">
        S H I V E R
      </text>
    </svg>`;
  const watermarkUrl = "data:image/svg+xml;base64," + btoa(watermarkSvg);

  // Calculate axis ranges
  let xaxis_range = null;
  let yaxis_range = null;

  if (globalMinX !== null && globalMaxX !== null && globalMinX !== globalMaxX) {
    const xRange = globalMaxX - globalMinX;
    const xBuffer = xRange * 0.03;
    xaxis_range = [new Date(globalMinX - xBuffer), new Date(globalMaxX + xBuffer)];
  }
  
  if (globalMinY !== Infinity && globalMaxY !== -Infinity) {
    const yRange = globalMaxY - globalMinY;
    const yBuffer = yRange === 0 ? globalMinY * 0.1 : yRange * 0.1;
    yaxis_range = [globalMinY - yBuffer, globalMaxY + yBuffer];
  }
  
  const layout = {
    images: [{
      source: watermarkUrl,
      xref: "paper", yref: "paper",
      x: 0.5, y: 0.5,
      sizex: 0.8, sizey: 0.8,
      xanchor: "center", yanchor: "middle",
      layer: "below",
      opacity: 1
    }],
    xaxis: { title: { text: 'Date', standoff: 15 }, showline: true, linewidth: 1, linecolor: 'black', mirror: true, automargin: true, type: 'date', range: xaxis_range, autorange: !xaxis_range },
    yaxis: { title: { text: yAxisLabel, standoff: 15 }, showline: true, linewidth: 1, linecolor: 'black', mirror: true, automargin: true, range: yaxis_range, autorange: !yaxis_range },
    margin: { t: 5, r: 20, l: 60, b: 40 }, 
    showlegend: colorBySource.value, 
    legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' },
    autosize: true
  };

  return { data: traces, layout };
};

// --- NEW HANDLER: Toggle Visibility ---
const togglePointVisibility = (id) => {
    const point = selectedPoints.value.find(p => p.id === id);
    if (point) {
        // Toggle property
        point.visible = point.visible === false ? true : false;
        // Trigger chart update
        updateChart();
    }
};

// PLOT CHART
const updateChart = async () => {
  await nextTick(); 
  
  // Handle empty state
  if (selectedPoints.value.length === 0) { 
      plotlyLib.value?.purge('velocity-chart'); 
      legendItems.value = []; 
      xAxisMin.value = ''; xAxisMax.value = '';
      yAxisMin.value = ''; yAxisMax.value = '';
      isUserZoomed.value = false;
      return; 
  }
  
  // Build data and configuration
  const { data, layout } = buildChartConfig(currentPlotVariable.value);
  
  // Zoom if user interacted
  if (isUserZoomed.value) {
      if (xAxisMin.value && xAxisMax.value) {
         layout.xaxis.range = [xAxisMin.value, xAxisMax.value];
         layout.xaxis.autorange = false;
      }
      
      if (yAxisMin.value !== '' && yAxisMax.value !== '') {
         layout.yaxis.range = [parseFloat(yAxisMin.value), parseFloat(yAxisMax.value)];
         layout.yaxis.autorange = false;
      }
  }
  
  // Adjust plotly configuration
  const config = {
    responsive: true,
	displayModeBar: true,
	displaylogo: false,
    // Add the specific button names you want to hide here
    modeBarButtonsToRemove: [
      'lasso2d',       // Lasso Select
      'select2d',      // Box Select
	  'toImage',       // Remove plotly image download (we replace with our own button that looks the same but performs better)
      'toggleSpikelines', // Toggle Spike Lines
	  'autoScale2D',   // Remove autoscale button (reset scale works just as well)
      'hoverClosestCartesian', // Often redundant if you use 'compare'
      'hoverCompareCartesian'  // Keep this if you want shared tooltips
    ],
	// -- Add your custom button
    modeBarButtonsToAdd: [
      {
        name: 'custom_download', // Internal name
        title: 'Download Plot (PNG)', // Tooltip text
        icon: plotlyLib.value.Icons.camera,    // Use Plotly's default camera icon
        click: function(gd) { downloadChartImage(); }
      },
	  {
        name: 'toggle_color_by_source',
        title: 'Toggle Colours: Site vs Data Source',
        icon: {
            width: 24, height: 24,
            // SVG path for a Color Palette icon
            path: "M12,2C6.48,2,2,6.48,2,12s4.48,10,10,10c1.21,0,2.12-1.07,1.86-2.26c-0.08-0.34-0.24-0.66-0.45-0.92 C13.2,18.55,13.06,18.27,13.06,18c0-0.55,0.45-1,1-1h1.56c3.53,0,6.38-2.85,6.38-6.38C22,5.46,17.52,2,12,2z M6.5,11.5 c-0.83,0-1.5-0.67-1.5-1.5s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S7.33,11.5,6.5,11.5z M9.5,7.5C8.67,7.5,8,6.83,8,6s0.67-1.5,1.5-1.5 s1.5,0.67,1.5,1.5S10.33,7.5,9.5,7.5z M14.5,7.5C13.67,7.5,13,6.83,13,6s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S15.33,7.5,14.5,7.5z M17.5,11.5c-0.83,0-1.5-0.67-1.5-1.5s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S18.33,11.5,17.5,11.5z"
        },
        click: function() {
            colorBySource.value = !colorBySource.value;
            updateChart(); // Redraw chart instantly!
        }
      }
    ],
  };
  
  // Render the plot
  let graphDiv = null;
  if (plotlyLib.value) {
    graphDiv = await plotlyLib.value.newPlot('velocity-chart', data, layout, config);
  }
  
  //Attach listener for axis updates
  if (graphDiv) {
    graphDiv.removeAllListeners && graphDiv.removeAllListeners('plotly_relayout');
    graphDiv.on('plotly_relayout', onPlotRelayout);
    
    // Populate initial values if not zoomed
    if (graphDiv.layout.xaxis && graphDiv.layout.xaxis.range) {
        const xRange = graphDiv.layout.xaxis.range;
        xAxisMin.value = formatChartDate(xRange[0]);
        xAxisMax.value = formatChartDate(xRange[1]);
    }

    if (graphDiv.layout.yaxis && graphDiv.layout.yaxis.range) {
        const yRange = graphDiv.layout.yaxis.range;
        yAxisMin.value = Math.round(yRange[0] * 100) / 100;
        yAxisMax.value = Math.round(yRange[1] * 100) / 100;
    }
	// Force resize
	window.requestAnimationFrame(() => {
        plotlyLib.value.Plots.resize(graphDiv);
    });
  }
};


const calculateRegression = (xDates, yValues) => {
  const n = xDates.length;
  if (n < 2) return null;

  // 1. Constants
  const MS_PER_YEAR = 1000 * 60 * 60 * 24 * 365.25;

  const x = xDates.map(d => new Date(d).getTime());
  const y = yValues;

  let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0, sumYY = 0;
  for (let i = 0; i < n; i++) {
    sumX += x[i];
    sumY += y[i];
    sumXY += x[i] * y[i];
    sumXX += x[i] * x[i];
    sumYY += y[i] * y[i];
  }

  // 2. Calculate Raw Slope (Change per Millisecond)
  const rawSlope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - rawSlope * sumX) / n;

  // 3. Convert to "Change per Year"
  const slopePerYear = rawSlope * MS_PER_YEAR;

  // 4. Stats (R2 and P)
  const ssTot = sumYY - (sumY * sumY) / n;
  const ssRes = sumYY - rawSlope * sumXY - intercept * sumY;
  const r2 = 1 - (ssRes / ssTot);

  const s2 = ssRes / (n - 2); 
  const seSlope = Math.sqrt(s2 / (sumXX - (sumX * sumX) / n));
  const tStat = rawSlope / seSlope;
  const pValue = getPValueFromT(Math.abs(tStat), n - 2);

  // Return both raw (for plotting) and converted (for display)
  return { slope: rawSlope, intercept, slopePerYear, r2, pValue };
};

// --- HANDLER: Toggle Trends ---
const toggleTrends = async () => {
  showTrends.value = !showTrends.value;

  if (showTrends.value) {
    // 1. Default the Trend Range to the CURRENT visible chart range
    // If user has zoomed, use that. If not, use global bounds.
    if (xAxisMin.value && xAxisMax.value) {
      trendStart.value = xAxisMin.value;
      trendEnd.value = xAxisMax.value;
    } else {
      // Fallback: Use the very first and last date of the data
      // (Simplified logic: grab from first point)
      if (selectedPoints.value.length > 0) {
        const dates = selectedPoints.value[0].data.data.dates;
        trendStart.value = dates[0];
        trendEnd.value = dates[dates.length - 1];
      }
    }
  }

  // 2. Refresh Chart
  await updateChart();
};

// --- HANDLER: Update when Trend Dates change ---
const updateTrendCalc = async () => {
   if (showTrends.value) {
     await updateChart();
   }
};

// Approximate two-tailed p-value from t-stat (Abramowitz & Stegun approx)
const getPValueFromT = (t, df) => {
  const x = df / (df + t * t);
  let p = 0; 
  // Beta function approximation loop
  // (Simplified for brevity: returns rough significance tiers if math is too heavy)
  // For a robust implementation without libraries, simple thresholds are often used in UI:
  if (Math.abs(t) > 3.291) return 0.001; // roughly p < 0.001
  if (Math.abs(t) > 2.576) return 0.01;  // roughly p < 0.01
  if (Math.abs(t) > 1.960) return 0.05;  // roughly p < 0.05
  return 0.10; // Not significant
};

const setWaitCursor = (shouldWait) => {
  if (shouldWait) {
    const style = document.createElement('style');
    style.id = 'global-wait-cursor';
    style.innerHTML = '* { cursor: wait !important; }'; // The "Nuclear" override
    document.head.appendChild(style);
  } else {
    const style = document.getElementById('global-wait-cursor');
    if (style) style.remove();
  }
};


// CHART IMAGE DOWNLOAD (MULTI-FILE + OPTIMIZED SNAPSHOT)
const downloadChartImage = async () => {
  if (selectedPoints.value.length === 0) return;
  
  const domToImageModule = await import('dom-to-image-more');
  const domtoimage = domToImageModule.default || domToImageModule;

  // 1. Identify Elements
  const chartContainer = document.querySelector('.chart-section'); 
  const graphDiv = document.getElementById('velocity-chart'); 

  if (!chartContainer || !graphDiv) {
      console.error("Could not find chart elements.");
      alert("Error: Chart container not found.");
      return;
  }

  statusMessage.value = "Processing charts...";
  setWaitCursor(true);
  
  // High quality scale
  const EXPORT_SCALE = 1; 
  const originalPlotVariable = currentPlotVariable.value;

  // 2. Wrap in timeout to allow UI to show "Processing..."
  setTimeout(async () => {
    let tempImg = null;
    const originalDisplay = graphDiv.style.display; 

    try {
      const zip = new JSZip(); // Instantiate once at the top
      
      const optionsProcess = plotOptions.value.length > 0 
          ? plotOptions.value 
          : [{val: currentPlotVariable.value, label: 'Current'}];
      
      const filesToSave = [];

      // --- START LOOP ---
      for (const opt of optionsProcess) {
        statusMessage.value = `Capturing ${opt.label || opt.val}...`;

        // A. Switch View & Wait for Render
        if (currentPlotVariable.value !== opt.val) {
            currentPlotVariable.value = opt.val;
            await nextTick();
            if (typeof updateChart === 'function') await updateChart();
            await new Promise(r => setTimeout(r, 800)); 
        }

        // B. Snapshot Plotly Vectors to PNG
        const plotlyDataUrl = await plotlyLib.value.toImage(graphDiv, {
            format: 'png',
            width: graphDiv.clientWidth * EXPORT_SCALE,
            height: graphDiv.clientHeight * EXPORT_SCALE,
            scale: 1 
        });

        // C. Swap: Hide Interactive Graph, Show Static Image
        tempImg = document.createElement('img');
        tempImg.src = plotlyDataUrl;
        tempImg.style.width = '100%'; 
        tempImg.style.height = '100%';
        tempImg.style.objectFit = 'contain';
        tempImg.style.display = 'block';
        
        graphDiv.parentNode.insertBefore(tempImg, graphDiv);
        graphDiv.style.display = 'none';

        // D. Capture Container (Legend + Static Image)
        const width = chartContainer.clientWidth;
        const height = chartContainer.clientHeight;

        const imgUrl = await domtoimage.toPng(chartContainer, {
            bgcolor: '#FFFFFF', 
            width: width * EXPORT_SCALE,
            height: height * EXPORT_SCALE,
            style: {
              transform: `scale(${EXPORT_SCALE})`,
              transformOrigin: 'top left',
              width: `${width}px`,
              height: `${height}px`
            },
            filter: (node) => {
                if (!node.classList) return true; 
                if (node.id === 'velocity-chart') return false; 
                if (node.classList.contains('chart-controls')) return false;
                if (node.classList.contains('chart-controls-overlay')) return false;
                if (node.classList.contains('axis-controls')) return false; 
                if (node.classList.contains('info-sidebar')) return false;

                const tag = node.tagName;
                if (['INPUT', 'SELECT', 'BUTTON', 'TEXTAREA'].includes(tag)) return false;
                if (tag === 'LABEL' && node.parentElement.classList.contains('axis-group')) return false;

                return true;
            }
        });

        // E. Store Result
        const blob = await (await fetch(imgUrl)).blob();
        
        const suffix = (typeof smoothingSuffix !== 'undefined' && smoothingSuffix.value) ? smoothingSuffix.value : '';
        const fname = `velocity_${opt.val}_timeseries${suffix}.png`;
        
        filesToSave.push({ name: fname, blob: blob });

        // F. Cleanup for next iteration
        if (tempImg) tempImg.remove();
        graphDiv.style.display = originalDisplay;

        await new Promise(resolve => setTimeout(resolve, 50)); 
      }
      // --- END LOOP ---

      // 3. Restore Original State
      if (currentPlotVariable.value !== originalPlotVariable) {
          currentPlotVariable.value = originalPlotVariable;
          await nextTick();
          if (typeof updateChart === 'function') await updateChart();
      }

      // ---------------------------------------------------------
      // 4. Generate and Add Citations & Summary CSV
      // ---------------------------------------------------------
      const sourceStats = {}; 
      
      selectedPoints.value.forEach(p => {
        const rootData = p.data?.data;
        if (!rootData) return;

        const excludeKeys = ['dates', 'dates_daily', 'speed_error', 'vx_error', 'vy_error', 'dt', 'count', 'data_source'];
        const availableKeys = Object.keys(rootData).filter(k => !excludeKeys.includes(k));

        if (rootData.dates) {
          rootData.dates.forEach((date, i) => {
            let isValid = true;
            if (availableKeys.length > 0) {
               const firstKey = availableKeys[0];
               const checkVal = rootData[firstKey]?.raw ? rootData[firstKey].raw[i] : rootData[firstKey][i];
               if (checkVal === null || checkVal === undefined || Number.isNaN(checkVal)) { 
                   isValid = false; 
               }
            }

            if (isValid) {
               const source = (rootData.data_source) ? rootData.data_source[i] : "SHIFT";
               
               if (source && source !== 'Unknown') {
                   if (!sourceStats[source]) {
                       sourceStats[source] = { firstDate: date, lastDate: date, dts: [], epochs: 0 };
                   }
                   
                   const stats = sourceStats[source];
                   stats.epochs++;
                   
                   if (date < stats.firstDate) stats.firstDate = date;
                   if (date > stats.lastDate) stats.lastDate = date;
                   
                   const dtVal = rootData.dt ? rootData.dt[i] : null;
                   if (dtVal !== null && dtVal !== undefined && !Number.isNaN(Number(dtVal))) {
                       stats.dts.push(Number(dtVal));
                   }
               }
            }
          });
        }
      });

      const uniqueSourcesArray = Object.keys(sourceStats);
      
      // Add the global text file
      const citationText = generateCitationText(uniqueSourcesArray, currentRegion.value, datasetVersion.value);
      zip.file("citations_and_usage.txt", citationText);

      // Mode helper (with the +1 fix)
      const getMode = (arr) => {
          if (!arr || arr.length === 0) return "N/A";
          const counts = {};
          let maxCount = 0;
          let mode = arr[0];
          for (const val of arr) {
              counts[val] = (counts[val] || 0) + 1;
              if (counts[val] > maxCount) {
                  maxCount = counts[val];
                  mode = val;
              }
          }
          return (Number(mode) + 1).toFixed(2);
      };

      // Build CSV
      let csvContent = "Data Source,First Date,Last Date,Mode Temporal Resolution (days),Epochs (Measurements),Citation\n";
      
      // 1. Add the SHIVER row first
      const shiverCitations = 
          "SHIVER data and compilation method: Davison, B. J. (2026). The SHeffield Ice Velocity ExploreR (SHIVER): A unified satellite-derived ice velocity dataset for Earth's ice sheets (Version v[specify version number]) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21375859\n" +
          "SHIVER method paper: Davison, B. J. et al. (in prep). The SHeffield Ice Velocity ExploreR (SHIVER): an online tool for low latency exploration, analysis and sub-setting of unified satellite-derived ice velocity data for Earth's ice sheets. [specify journal]. https://doi.org/10.xxxx/XXXXXXX";
      
      csvContent += `SHIVER,,,,,"${shiverCitations.replace(/"/g, '""')}"\n`;
      
      // 2. Loop through unique sources
      uniqueSourcesArray.forEach(source => {
          const stats = sourceStats[source];
          const modeVal = getMode(stats.dts);
          const fullCite = generateCitationText([source], currentRegion.value, datasetVersion.value);
          
          let cleanCite = "";
          const delimiter = "cite these original sources:\n\n* ";
          if (fullCite.includes(delimiter)) {
              cleanCite = fullCite.split(delimiter)[1].trim();
          } else {
              const parts = fullCite.split("* ");
              cleanCite = parts[parts.length - 1].trim();
          }
          
          const escapedCite = `"${cleanCite.replace(/"/g, '""')}"`;
          csvContent += `${source},${stats.firstDate},${stats.lastDate},${modeVal},${stats.epochs},${escapedCite}\n`;
      });
      
      zip.file("citations_summary.csv", csvContent);
      // ---------------------------------------------------------

      // 5. Package Everything into Zip
      statusMessage.value = "Compressing package...";
      filesToSave.forEach(f => zip.file(f.name, f.blob));
      
      const content = await zip.generateAsync({type:"blob"});
      
      // Determine Zip Name: specific if 1 chart, generic if multiple
      let zipName = `Velocity_Charts_${currentRegion.value || 'Region'}.zip`;
      if (filesToSave.length === 1) {
          const baseName = filesToSave[0].name.replace('.png', '');
          zipName = `${baseName}_package.zip`;
      }
      
      saveAs(content, zipName);
      statusMessage.value = "Chart package downloaded.";

      // 6. Log the Download (Backend)
      const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
      if (token && content) {
          apiClient.post('/api/users/log', { 
             interaction_type: 'chart_export', 
             filename: zipName,
             file_size_mb: content.size / (1024 * 1024)
          }, {
             headers: { Authorization: `Bearer ${token}` }
          }).catch(e => console.error("Logging failed", e));
      }

    } catch (error) {
      console.error("Chart Export Error:", error);
      statusMessage.value = "Error generating chart.";
    } finally {
      // Final safety cleanup
      if (tempImg && tempImg.parentNode) tempImg.remove();
      if (graphDiv) graphDiv.style.display = originalDisplay;

      setWaitCursor(false);
      setTimeout(() => statusMessage.value = "", 2000);
    }
  }, 50);
};

// Helper: Generates filenames for download
const getFilename = (p, index) => {
  const meta = p.data.meta || {};
  let name = meta.site_name || p.name || 'Site';
  if (/^Site_\d+$/.test(name)) name = `Site_${index + 1}`;
  const buf = meta.buffer_used !== undefined ? meta.buffer_used : pendingBuffer.value;
  // Use toFixed(3) for lat/lon as requested previously + params
  const lat = p.lat.toFixed(3);
  const lon = p.lon.toFixed(3);
  return `${name}_${buf}m_${lat}_${lon}${smoothingSuffix.value}.xlsx`;
};

// --- DATA DOWNLOAD HANDLER ---
const handleDownload = async () => {
  if (selectedPoints.value.length === 0) return;

  // Track downloads (Always a ZIP now)
  trackEvent("file_download", {
      event_category: "export",
      event_label: "zip_data_package", 
      file_extension: "zip", 
      file_name: selectedPoints.value.length === 1 
          ? `${getFilename(selectedPoints.value[0], 0)}_package` 
          : "velocity_data_batch",
      region: currentRegion.value,
      count: selectedPoints.value.length
  });

  isDownloading.value = true;
  
  try {
    const zip = new JSZip();
    
    // 1. Add XLSX Files to Zip
    selectedPoints.value.forEach((p, index) => {
      const wb = generateXLSX(p, index);
      const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
      zip.file(getFilename(p, index), wbout);
    });

    // 2. Add GeoJSON Summary (Always included)
    const geojson = {
      type: "FeatureCollection",
      features: selectedPoints.value.map((p, index) => {
        let name = p.name || `Site_${p.id}`;
        if (/^Site_\d+$/.test(name)) name = `Site_${index + 1}`;

        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [p.lon, p.lat] 
          },
          properties: {
            id: index + 1,
            name: name,
            buffer_m: p.data.meta?.buffer_used || pendingBuffer.value,
            region: currentRegion.value
          }
        };
      })
    };

    zip.file("sites.geojson", JSON.stringify(geojson, null, 2));
    
    
    // ---------------------------------------------------------
    // 3. Extract Stats, Citations, and build CSV
    // ---------------------------------------------------------
    const sourceStats = {}; 
    
    selectedPoints.value.forEach(p => {
      const rootData = p.data?.data;
      if (!rootData) return;
      
      // IDENTIFY VARIABLES
      const excludeKeys = ['dates', 'dates_daily', 'speed_error', 'vx_error', 'vy_error', 'dt', 'count', 'data_source'];
      const availableKeys = Object.keys(rootData).filter(k => !excludeKeys.includes(k));

      // LOOP THROUGH ROWS TO FIND VALID DATA & TRACK STATS
      if (rootData.dates) {
        rootData.dates.forEach((date, i) => {
          
          let isValid = true;
          if (availableKeys.length > 0) {
             const firstKey = availableKeys[0];
             const checkVal = rootData[firstKey]?.raw ? rootData[firstKey].raw[i] : rootData[firstKey][i];
             if (checkVal === null || checkVal === undefined || Number.isNaN(checkVal)) { 
                 isValid = false; 
             }
          }

          if (isValid) {
             // Determine source (Default to SHIFT if single-source)
             const source = (rootData.data_source) ? rootData.data_source[i] : "SHIFT";
             
             if (source && source !== 'Unknown') {
                 // Initialize stats object for this source if it doesn't exist yet
                 if (!sourceStats[source]) {
                     sourceStats[source] = { firstDate: date, lastDate: date, dts: [], epochs: 0 };
                 }
                 
                 const stats = sourceStats[source];
                 stats.epochs++;
                 
                 // Update min/max dates (YYYY-MM-DD strings sort alphabetically)
                 if (date < stats.firstDate) stats.firstDate = date;
                 if (date > stats.lastDate) stats.lastDate = date;
                 
                 // Track dt (time_separation) for the mode calculation
                 const dtVal = rootData.dt ? rootData.dt[i] : null;
                 if (dtVal !== null && dtVal !== undefined && !Number.isNaN(Number(dtVal))) {
                     stats.dts.push(Number(dtVal));
                 }
             }
          }
        });
      }
    });

    const uniqueSourcesArray = Object.keys(sourceStats);
    
    // Generate and add the global text file
    const citationText = generateCitationText(uniqueSourcesArray, currentRegion.value, datasetVersion.value);
    zip.file("citations_and_usage.txt", citationText);

    // --- Helper to calculate the Mode of the dt array ---
    const getMode = (arr) => {
        if (!arr || arr.length === 0) return "N/A";
        const counts = {};
        let maxCount = 0;
        let mode = arr[0];
        for (const val of arr) {
            counts[val] = (counts[val] || 0) + 1;
            if (counts[val] > maxCount) {
                maxCount = counts[val];
                mode = val;
            }
        }
		return (Number(mode) + 1).toFixed(2);
    };

    // --- Build and add the CSV file ---
    let csvContent = "Data Source,First Date,Last Date,Mode Temporal Resolution (days),Epochs (Measurements),Citation\n";
    
    // 1. Add the SHIVER row first
    const shiverCitations = 
          "SHIVER data and compilation method: Davison, B. J. (2026). The SHeffield Ice Velocity ExploreR (SHIVER): A unified satellite-derived ice velocity dataset for Earth's ice sheets (Version v[specify version number]) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21375859\n" +
          "SHIVER method paper: Davison, B. J. et al. (in prep). The SHeffield Ice Velocity ExploreR (SHIVER): an online tool for low latency exploration, analysis and sub-setting of unified satellite-derived ice velocity data for Earth's ice sheets. [specify journal]. https://doi.org/10.xxxx/XXXXXXX";
    
    // Empty commas represent the blank data columns
    csvContent += `SHIVER,,,,,"${shiverCitations.replace(/"/g, '""')}"\n`;
    
    // 2. Loop through unique sources
    uniqueSourcesArray.forEach(source => {
        const stats = sourceStats[source];
        const modeVal = getMode(stats.dts);
        const fullCite = generateCitationText([source], currentRegion.value, datasetVersion.value);
        
        // Isolate the underlying data citation
        let cleanCite = "";
        const delimiter = "cite these original sources:\n\n* ";
        
        if (fullCite.includes(delimiter)) {
            cleanCite = fullCite.split(delimiter)[1].trim();
        } else {
            // Fallback
            const parts = fullCite.split("* ");
            cleanCite = parts[parts.length - 1].trim();
        }
        
        const escapedCite = `"${cleanCite.replace(/"/g, '""')}"`;
        
        csvContent += `${source},${stats.firstDate},${stats.lastDate},${modeVal},${stats.epochs},${escapedCite}\n`;
    });
    
    zip.file("citations_summary.csv", csvContent);
    // ---------------------------------------------------------


    // 4. Generate and Save
    const content = await zip.generateAsync({ type: "blob" });
    
    let zipName = "velocity_data_batch.zip";
    if (selectedPoints.value.length === 1) {
        const baseName = getFilename(selectedPoints.value[0], 0).replace('.xlsx', '');
        zipName = `${baseName}_data.zip`;
    }

    saveAs(content, zipName);
    
    // log downloads
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
    if (token) {
        apiClient.post('/api/users/log', {
            interaction_type: 'data_download',
            filename: zipName,
            file_size_mb: content.size / (1024 * 1024)
        }, {
            headers: { Authorization: `Bearer ${token}` }
        }).catch(e => console.error("Logging failed", e));
    }

  } catch (e) {
    statusMessage.value = "Zip Error.";
    console.error(e);
  } finally {
    isDownloading.value = false;
  }
};

const generateXLSX = (point, index) => {
  const rootData = point.data.data; 
  const wb = XLSX.utils.book_new();
  
  if (!rootData) return wb;
  
  // 1. IDENTIFY VARIABLES
  const excludeKeys = ['dates', 'dates_daily', 'speed_error', 'vx_error', 'vy_error', 'dt', 'count', 'data_source'];
  const availableKeys = Object.keys(rootData).filter(k => !excludeKeys.includes(k));
  const displayKeys = availableKeys.map(key => `${key}_m_yr`);

  // ==========================================
  // SHEET 1: POINT DATA (Skips NaNs)
  // ==========================================
  const pointRows = [];
  
  // Create headers dynamically
  let pointHeaders = [];
  pointHeaders = ["Date", "Data_Source", "speed_error_m_yr", "vx_error_m_yr", "vy_error_m_yr", "time_separation_days", "pixel_count", ...displayKeys];
  pointRows.push(pointHeaders);

  rootData.dates.forEach((date, i) => {
     // Check for NaN in the first available variable (usually 's')
     if (availableKeys.length > 0) {
        const firstKey = availableKeys[0];
        const checkVal = rootData[firstKey]?.raw ? rootData[firstKey].raw[i] : rootData[firstKey][i];
        if (checkVal === null || checkVal === undefined || Number.isNaN(checkVal)) { return; } // SKIP ROW
     }

     const errorMag = rootData.speed_error ? rootData.speed_error[i] : '';
     const dt = rootData.dt ? rootData.dt[i] : '';
     const count = rootData.count ? rootData.count[i] : 0;

     // Construct the base row dynamically
     let row = [];
	 const source = rootData.data_source ? rootData.data_source[i] : 'Unknown';
	 const errorVX = rootData.vx_error ? rootData.vx_error[i] : '';
	 const errorVY = rootData.vy_error ? rootData.vy_error[i] : '';
	 row = [date, source, errorMag, errorVX, errorVY, dt, count];
	 
	 // Append the actual velocity variables
     availableKeys.forEach(k => {
         const val = rootData[k]?.raw ? rootData[k].raw[i] : rootData[k][i];
         row.push(val !== null && val !== undefined ? val : '');
     });
     pointRows.push(row);
  });

  const wsPoint = XLSX.utils.aoa_to_sheet(pointRows);
  XLSX.utils.book_append_sheet(wb, wsPoint, "Point Data");

  // ==========================================
  // SHEET 2: DAILY DATA (Keeps NaNs)
  // ==========================================
  // Assuming 'dates_daily' exists in your data structure. 
  // If not, fallback to 'dates' or an empty array.
  const dailyDates = rootData.dates_daily || rootData.dates; 
  
  if (dailyDates && dailyDates.length > 0) {
      const dailyRows = [];
      const dailyHeaders = ["Date", ...displayKeys];
      dailyRows.push(dailyHeaders);

      dailyDates.forEach((date, i) => {
          const row = [date];
          availableKeys.forEach(k => {
              const val = rootData[k]?.smoothed ? rootData[k].smoothed[i] : null;
              row.push(val !== null && val !== undefined ? val : ''); 
          });
          dailyRows.push(row);
      });

      const wsDaily = XLSX.utils.aoa_to_sheet(dailyRows);
      XLSX.utils.book_append_sheet(wb, wsDaily, "Daily Data");
  }

  // ==========================================
  // SHEET 3: METADATA
  // ==========================================
  const meta = point.data.meta || {};
  let siteName = meta.site_name || point.name || `Site_${point.id}`;
  if (/^Site_\d+$/.test(siteName)) { siteName = `Site_${index + 1}`; }
  const metaRows = [
      ["Property", "Value"], // Header
      ["Site Name", siteName],
      ["Latitude", point.lat],
      ["Longitude", point.lon],
      ["Buffer (m)", meta.buffer_used || pendingBuffer.value],
      ["Region", currentRegion.value],
      ["Smoothing Suffix", smoothingSuffix.value],
      ["Export Date", new Date().toISOString()]
  ];
  
  // Log the specific query settings used for this point
  metaRows.push(["Sources", point.settings.sources.join(', ')]);
  metaRows.push(["Variables", point.settings.variable.join(', ')]);

  const wsMeta = XLSX.utils.aoa_to_sheet(metaRows);
  XLSX.utils.book_append_sheet(wb, wsMeta, "Metadata");

  return wb;
};



// ==========================================================
// =========== GUEST TOUR ======================================
// ==========================================================
onMounted(async () => {
  await nextTick(); // Wait for the DOM to be ready

  // 1. Check for the token directly
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;
  let hasCompletedTour = false;

  // 2. Determine tour status
  if (token) {
    // USER IS LOGGED IN: Ask FastAPI if they have completed the tour
    try {
      const config = { headers: { 'Authorization': `Bearer ${token}` } };
      // Replace this with your actual endpoint that returns the user's profile
      const response = await apiClient.get('/api/users/me', config); 
      
      // Assuming your backend returns a boolean field called 'has_completed_tour'
      hasCompletedTour = response.data.has_completed_tour; 
    } catch (error) {
      console.error("Failed to fetch user profile:", error);
      // Fallback: if the request fails, assume they haven't completed it so the tour runs
      hasCompletedTour = false; 
    }
  } else {
    // USER IS A GUEST: Check local storage
    hasCompletedTour = localStorage.getItem('app_tour_status') === 'completed';
  }

  // 3. Launch the tour if they haven't completed it
  if (!hasCompletedTour) {
    setTimeout(() => {
      
      startGuestTour(
        // Callback 1: Tour Complete
        async () => {
          if (token) {
            try {
              const config = { headers: { 'Authorization': `Bearer ${token}` } };
              await apiClient.patch('/api/users/me/tour-status', { tour_status: 'completed' }, config);
              console.log("Backend updated successfully.");
            } catch (error) {
              console.error("Failed to save tour status:", error);
            }
          } else {
            localStorage.setItem('app_tour_status', 'completed');
          }
        },
        // Callback 2: Set status message
        (msg) => {
          statusMessage.value = msg;
        }
      );
      
    }, 1000);
  }
});

// REPLAY TOUR
const replayTour = () => {
  showHelp.value = false; // 1. Close the help pop-up
  
  setTimeout(() => {
    startGuestTour();     // 2. Launch the tour after a brief pause
  }, 300); // 300ms allows the modal fade-out animation to finish
};

// Point to your video path
const tutorialVideoSrc = ref('https://www.youtube.com/embed/O4mW5bOfp8g?si=SjTWUKv9DZ5eO2tC');


</script>

<style scoped>
/* --- MAIN LAYOUT --- */
.page-container { display: flex; flex-direction: column; height: calc(100vh - 60px); width: 100%; overflow: hidden; }
.map-wrapper { position: relative; width: 100%; user-select: none; container-type: size; container-name: map-container }
.chart-wrapper { width: 100%; background: white; position: relative; overflow: hidden; display: flex; flex-direction: column;}
.chart-container { width: 100%; flex: 1; min-height: 0;}
.chart-controls-overlay {
  position: absolute; top: 5px; right: 35px; z-index: 100;  display: flex; 
  align-items: center; gap: 8px; background-color: rgba(255, 255, 255, 0.9); 
  padding: 4px 8px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
  font-size: 0.85rem;
}
.overlay-select { padding: 2px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem; background-color: white; }

.resize-handle {
  width: 100%;
  height: 2px; /* Hit area height */
  background-color: #f1f1f1;
  cursor: row-resize; /* The up/down arrow cursor */
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #ccc;
  border-bottom: 1px solid #ccc;
  flex-shrink: 0; /* Prevent the handle itself from squishing */
  z-index: 2000; /* Ensure it sits above map controls */
  position: relative;
  touch-action: none;
}

/* Add an invisible touch target, to make it easier to hit on a phone */
.resize-handle::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -15px;    /* Extend 15px Up */
  bottom: -15px; /* Extend 15px Down */
  z-index: 2500; /* Sit on top of everything */
  cursor: row-resize;
}

.resize-handle:hover { background-color: #e0e0e0; }

/* The little visual "grip" lines in the middle */
.handle-grip { width: 40px; height: 4px; border-top: 2px solid #999; border-bottom: 2px solid #999; }


/* --- MAIN CONTROLS--- */ 
.map-toolbar {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000; /* Above Leaflet Map */
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.map-toolbar-left {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 1000; /* Above Leaflet Map */
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}


/* The wrapper holds the actual button groups */
.tools-wrapper {
  display: flex;
  flex-direction: column;
  gap: 15px;
  transition: opacity 0.2s ease;
}

.toolbar-group {
  display: flex;
  flex-direction: column;
  gap: 8px; /* Space between buttons in a group */
  background: rgba(255, 255, 255, 0.9);
  padding: 8px;
  border-radius: 20px; /* Capsule shape container */
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  backdrop-filter: blur(4px);
}

.toolbar-group-row {
  display: flex;
  flex-direction: row;
  gap: 8px; /* Space between buttons in a group */
  background: rgba(255, 255, 255, 0.9);
  padding: 8px;
  border-radius: 20px; /* Capsule shape container */
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  backdrop-filter: blur(4px);
}

/* The Hamburger Menu Button (Hidden by default) */
.menu-trigger {
  display: none; 
  margin-bottom: 10px;
}
.menu-trigger .panel-btn {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 6px rgba(0,0,0,0.15);
  width: 40px;
  height: 40px;
  border-radius: 50%; /* Circle shape for the trigger */
}

/* --- RESPONSIVE LOGIC --- */
/* If the screen height is less than 750px, switch to Compact Mode */
@container map-container (height < 400px) {
  
  /* 1. Show the hamburger button */
  .menu-trigger {
    display: block;
  }

  /* 2. Hide the tools by default */
  .tools-wrapper {
    /* Hidden state */
    opacity: 0;
    visibility: hidden; /* Use visibility instead of pointer-events */
    position: absolute;
    top: 0;
    right: 50px;
    flex-direction: row-reverse; 
    align-items: flex-start;
    /* pretty transition */
    transition: 
      opacity 0.3s ease 0.5s, 
      visibility 0s linear 0.8s;
  }

  /* 3. On Hover: Reveal the tools */
  .map-toolbar:hover .tools-wrapper {
    opacity: 1;
    visibility: visible;
    transition: 
      opacity 0.2s ease 0s, 
      visibility 0s linear 0s;
  }
}
.region-toggles, .header-actions {
  display: flex;
  gap: 12px; /* Space between buttons */
}

.panel-btn {
  width: 45px;
  height: 45px;
  border-radius: 50%; /* Makes them perfectly circular */
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;       /* White background by default */
  border: 1px solid #ddd; /* Subtle grey border */
  color: #555;            /* Grey icon/text */
  font-size: 1.25rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

/* Update .panel-btn to handle SVGs with strokes (like the upload icon) */
.panel-btn svg {
  fill: currentColor; 
  stroke: currentColor; 
}

/* Ensure the fill-based icons (like the Gear) don't get messed up by stroke */
.panel-btn svg[fill="currentColor"] {
  stroke: none;
}

.panel-btn svg path[stroke="#2c3e50"] {
  stroke: currentColor; /* Matches the button text color (grey or white) */
  fill: transparent;
}

/* A smaller spinner specifically for inside the buttons */
.spinner-small {
  display: inline-block;
  width: 14px;  /* Fits nicely inside the 32px button */
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff; /* White spinner looks great on the blue active background */
  animation: spin 0.8s linear infinite;
}

/* (Make sure you still have your @keyframes spin defined from before!) */
@keyframes spin { to { transform: rotate(360deg); } }

/* HOVER STATE (When mouse is over) */
.panel-btn:hover {
  border-color: #888;     /* Darker border */
  color: #333;            /* Darker text */
  background: #f8f9fa;    /* Very light grey fill */
}

/* ACTIVE STATE (Selected Region or Open Menu) */
.panel-btn.active {
  background: #2c3e50;    /* Dark Blue fill */
  border-color: #2c3e50;  /* match fill */
  color: #fff;            /* White text/icon */
}

/* Ensure disabled buttons look inactive */
.panel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #f0f0f0;
}


/*------------------------------------*/
/* --- 2. BOTTOM DASHBOARD LAYOUT --- */
/*------------------------------------*/
.bottom-dashboard {
  display: flex;
  width: 100%;
  background: white;
  border-top: 1px solid #ddd;
  overflow: hidden; /* Prevent double scrollbars */
}

/* Left: Chart */
.chart-section {
  flex: 1; /* Takes all available space */
  position: relative;
  min-width: 0; /* Flexbox safety */
  padding: 10px;
  display: flex;
  flex-direction: column;
}

/* Right: Site Info Sidebar */
.info-sidebar {
  width: 300px; /* Fixed width for the list */
  border-left: 1px solid #eee;
  display: flex;
  flex-direction: column;
  background: #f9f9f9;
}

.info-sidebar.empty {
  align-items: center;
  justify-content: center;
  color: #999;
  font-style: italic;
  padding: 20px;
  text-align: center;
}

/* Info Header (Buffer + Clear) */
.info-header {
  padding: 10px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
}

.info-header input {
  width: 60px;
  margin-left: 5px;
  padding: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.btn-text-only {
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 0.8rem;
  font-weight: bold;
  cursor: pointer;
}
.btn-text-only:hover { text-decoration: underline; }

/* Scrollable List Area */
.info-list-container {
  flex: 1; /* Fills remaining vertical space */
  overflow-y: auto;
  padding: 0;
}

/* Compact Table Styling */
.points-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.points-table th {
  text-align: left;
  padding: 8px;
  background: #eee;
  color: #666;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.points-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #f0f0f0;
}

.points-table input {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  font-family: monospace;
}
.points-table input:focus {
  border-color: #3498db;
  background: white;
}

.btn-remove-icon {
  border: none;
  background: none;
  color: #999;
  font-size: 1.2rem;
  cursor: pointer;
  line-height: 1;
}
.btn-remove-icon:hover { color: #e74c3c; }

/* --- MOBILE RESPONSIVENESS FOR BOTTOM-DASHBOARD --- */
@media (max-width: 900px) {
  
  /* 1. Stack the dashboard vertically */
  .bottom-dashboard {
    flex-direction: column;
    /* Allow the dashboard container to scroll vertically 
       because the stacked content (Chart + List) might be taller 
       than the allocated screen height */
    overflow-y: auto !important; 
    overflow-x: hidden;
  }

  /* 2. Give the chart a fixed height */
  .chart-section {
    width: 100%;
    /* flex: none ensures it doesn't try to shrink to fit the screen.
       It will force the dashboard to scroll if needed. */
    flex: none; 
    height: 350px; /* Enough space for Plotly to be readable */
    border-bottom: 1px solid #ddd;
  }

  /* 3. Make the sidebar full width */
  .info-sidebar {
    width: 100%;
    height: auto; /* Let it grow based on content */
    border-left: none; /* Remove side border */
    border-top: 1px solid #eee; /* Add top border */
    flex: none;
  }

  /* 4. Restrict the table height (Optional) */
  /* This prevents the table from becoming 5000px long if you have many points,
     forcing the user to scroll forever to get back to the chart. */
  .info-list-container {
    max-height: 300px; 
    overflow-y: auto;
  }
}

/* --- BRANDING (SHIVER) --- */
/* --- 1. FLOATING TITLE OVERLAY --- */
.map-title-overlay {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%); /* Centers the div perfectly */
  z-index: 1000; /* Ensures it sits above the map layers */
  
  background: rgba(255, 255, 255, 0.9); /* Semi-transparent white */
  backdrop-filter: blur(4px); /* Nice "frosted glass" effect */
  padding: 10px 25px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.15);
  
  text-align: center;
  pointer-events: none; /* Allows clicks to pass through transparent areas */
  border: 1px solid rgba(0,0,0,0.1);
}

.shiver-title {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 800;
  color: #0b1e3b;
  letter-spacing: 1px;
  line-height: 1;
}

.shiver-subtitle {
  font-size: 0.75rem;
  color: #0077B6;
  margin-top: 4px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

/* mobile resize */
@media (max-width: 768px) {
  .map-title-overlay {
    top: 10px;
    padding: 6px 15px;
    width: 25%; /* Prevent it from being too wide on phones */
  }
  
  .shiver-title {
    font-size: 1.2rem;
  }
  
  .shiver-subtitle {
    display: none; /* Hide subtitle on very small screens to save space */
  }
}



/* --- 3. MODERN ADVANCED POPUP --- */

/* 1. The Invisible Container */
/* This centers the popup but lets clicks pass through to the map */
.advanced-popup-container {
  position: absolute;
  
  /* Fill the entire parent (.map-wrapper) */
  inset: 0;  /* Short for top:0; right:0; bottom:0; left:0; */
  
  z-index: 2000;
  pointer-events: none; /* KEY: Allows clicking the map behind! */
  
  display: flex;
  justify-content: center;
  align-items: flex-start; /* Aligns to top, but with margin */
  padding-top: 60px; /* Space from the top of the map */
  padding-bottom: 20px; /* Space from bottom of map */
}

/* 2. The Card Itself */
.advanced-card {
  pointer-events: auto; /* Re-enable clicks inside the card */
  width: 380px;
  max-width: 90%;
  max-height: 95%; 
  display: flex;
  flex-direction: column; /* Stack Header, Body, Footer */
  
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px); /* Modern frosted glass effect */
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05);
  overflow: hidden; /* Clips children to rounded corners */
  
  /* Slide-in Animation */
  animation: slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideDown {
  from { transform: translateY(-20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* POSITION OVERRIDE
  Your advanced popup centers itself perfectly. 
  For the layers, you probably want it floating near the right-side toolbar. 
*/
.layer-popup-override {
  justify-content: flex-end; /* Align to the right */
  padding-right: 80px;       /* Keep it left of your toolbar */
}

/* Make the tab pills stretch to fill the container equally */
.tab-grid {
  display: flex;
  width: 100%;
}
.tab-pill {
  flex: 1;
  text-align: center;
}
.tab-pill span {
  display: block;
  width: 100%;
  box-sizing: border-box;
}

/* --- RECTANGULAR TABS --- */
.custom-tabs {
  display: flex;
  background: white;
  border-radius: 8px; /* Outer rounding only */
  border: 1px solid #dcdcdc;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.tab-btn {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #7f8c8d;
  cursor: pointer;
  background: #f8f9fa; /* Slightly off-white when inactive */
  transition: all 0.2s ease;
  margin: 0; /* Remove default label margins */
}

/* Hover state for inactive tabs */
.tab-btn:hover:not(.active) {
  background: #fff;
  color: #34495e;
}

/* Pressed/Active state */
.tab-btn.active {
  background: #e8f4fd; /* A subtle blue tint */
  color: #2c3e50;
  /* The inset shadow makes it look physically pressed down */
  box-shadow: inset 0 3px 6px rgba(0,0,0,0.1); 
}

.tab-btn span {
  display: block;
}

/* The vertical divider line */
.tab-divider {
  width: 1px;
  background: #dcdcdc;
}

/* Modern Select Dropdown to match your inputs */
.modern-select {
  width: 100%;
  padding: 8px 12px;
  background-color: #f1f3f5;
  border: 1px solid transparent;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.85rem;
  color: #555;
  cursor: pointer;
  outline: none;
  transition: all 0.2s ease;
  appearance: none; /* Removes native OS arrow */
  background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23555%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
  background-repeat: no-repeat;
  background-position: right 12px top 50%;
  background-size: 10px auto;
}
.modern-select:hover {
  background-color: #e2e6ea;
}
.modern-select:focus {
  border-color: #3498db;
  background-color: #fff;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
}

/* --- HEADER --- */
.card-header {
  padding: 15px 20px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
}
.card-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn-restore {
  background: none;
  border: none;
  color: #95a5a6;
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: underline;
}
.btn-restore:hover { color: #e74c3c; }
.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  color: #bdc3c7;
  cursor: pointer;
  padding: 0;
}
.btn-close:hover { color: #2c3e50; }

/* --- BODY (SCROLLABLE) --- */
.card-body {
  flex: 1; /* Fills available space */
  overflow-y: auto; /* Scrolls if content is too tall */
  padding: 20px;
}

.opt-group { margin-bottom: 20px; }
.group-label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #7f8c8d;
  font-weight: 750;
  margin-bottom: 10px;
}
.divider {
  border: 0;
  border-top: 1px solid rgba(0,0,0,0.06);
  margin: 20px 0;
}

/* Select/Deselect All buttons */
.group-header {
    display: flex;
    justify-content: space-between; /* Puts label on the left, buttons on the right */
    align-items: center;
    margin-bottom: 10px;
}

.bulk-actions {
    display: flex;
    gap: 8px; /* Space between the two buttons */
}

.bulk-btn {
    background-color: #f0f0f0;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 0.85rem;
	font-weight: 300;
    cursor: pointer;
    color: #333;
    transition: background-color 0.2s ease;
}

.bulk-btn:hover {
    background-color: #e0e0e0;
}

/* Modern Checkbox "Pills" */
.checkbox-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.checkbox-pill {
  position: relative;
  cursor: pointer;
}
.checkbox-pill input {
  position: absolute; opacity: 0; width: 0; height: 0;
}
.checkbox-pill span {
  display: inline-block;
  padding: 6px 12px;
  background: #f1f3f5;
  border-radius: 20px;
  font-size: 0.85rem;
  color: #555;
  transition: all 0.2s;
  border: 1px solid transparent;
}
/* Selected State */
.checkbox-pill input:checked + span {
  background: #e8f4fd;
  color: #3498db;
  border-color: #3498db;
  font-weight: 500;
}
/* Disabled state */
.checkbox-pill.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  filter: grayscale(100%);
}
/* Ensure the cursor applies to the span/input inside the label too */
.checkbox-pill.is-disabled * {
  cursor: not-allowed;
  pointer-events: none; /* Stops the hover state on child elements */
}
/* Prevent hover effects on enabled pill */
.checkbox-pill:not(.is-disabled):hover span {
  transform: translateY(-2px); /* Lifts the button up */
  box-shadow: 0 4px 8px rgba(52, 152, 219, 0.15); /* Soft blue shadow */
  border-color: #3498db; /* Blue outline */
  color: #3498db; /* Turns the text blue */
}

/* ANALYSIS BUTTON
/* Analysis Action Button */
.btn-run-analysis {
  /* Layout & Typography */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 10px 20px;
  border-radius: 20px; /* Matching your pill radius */
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  
  /* Visuals (Inherited from your active pill state) */
  background: #e8f4fd;
  color: #3498db;
  border: 1px solid #3498db;
}

/* Hover effect - re-using your "lift" and shadow logic */
.btn-run-analysis:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.2);
  background: #3498db; /* Invert colors on hover for a "pushed" feel */
  color: #ffffff;
}

/* Active/Click state */
.btn-run-analysis:not(:disabled):active {
  transform: translateY(0);
}

/* Disabled state - Matching your grayscale/opacity logic */
.btn-run-analysis:disabled {
  opacity: 0.5;
  filter: grayscale(100%);
  cursor: not-allowed;
  background: #f1f3f5;
  color: #555;
  border-color: transparent;
}

/* Inline Spinner for the button */
.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: btn-spin 0.75s linear infinite;
}

@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

/* Sliders */
.param-item { margin-bottom: 12px; }
.param-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #2c3e50;
  margin-bottom: 4px;
}
.param-val { font-weight: 600; color: #3498db; }
.param-val-input {
  width: 70px;
  text-align: right;
  font-weight: bold;
  color: #333; /* Adjust to match your theme */
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 2px 4px;
  background-color: transparent;
  outline: none;
}

.param-val-input:focus {
  border-color: #007bff; /* Add a nice highlight color when editing */
}

.modern-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #e0e0e0;
  outline: none;
}
.modern-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3498db;
  cursor: pointer;
  transition: transform 0.1s;
}
.modern-slider::-webkit-slider-thumb:hover { transform: scale(1.2); }

/* --- FOOTER --- */
.card-footer {
  flex-shrink: 0;
  padding: 15px 20px;
  background: white;
  border-top: 1px solid rgba(0,0,0,0.05);
  display: flex;
  justify-content: center;
}
.btn-primary-action {
  width: 100%;
  padding: 10px;
  background: #2c3e50;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-primary-action:hover { background: #34495e; }
.btn-primary-action:disabled { background: #95a5a6; cursor: not-allowed; }

/* Custom Scrollbar for the body */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0,0,0,0.1); border-radius: 3px; }

/* --- HELP MODAL OVERLAY --- */
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.6); display: flex; justify-content: center; align-items: center;
  z-index: 9999; backdrop-filter: blur(2px);
}
.modal-content {
  background: white; padding: 30px; width: 90%; max-width: 600px;
  border-radius: 12px; box-shadow: 0 15px 50px rgba(0,0,0,0.3);
  position: relative; max-height: 85vh; overflow-y: auto;
}
.modal-content h2 { margin-top: 0; color: #0056b3; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 20px; }
.modal-content h3 { font-size: 1.1rem; color: #333; margin-bottom: 8px; margin-top: 20px; }
.modal-content p, .modal-content li { color: #555; line-height: 1.6; font-size: 0.95rem; }
.modal-close { position: absolute; top: 15px; right: 20px; background: none; border: none; font-size: 28px; color: #999; cursor: pointer; }
.modal-close:hover { color: #333; }

/* --- PANEL COMPONENTS --- */
.panel-section { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.panel-section label { font-weight: bold; margin-right: 10px; color: #333; }
.panel-section select { padding: 5px; border-radius: 4px; border: 1px solid #ccc; width: 60%; }

.upload-section { margin-bottom: 15px; text-align: center; }
.btn-upload { display: inline-block; padding: 8px 12px; background: #6c757d; color: white; border-radius: 4px; cursor: pointer; font-size: 0.9rem; font-weight: bold; width: 100%; }

.list-toolbar { display: flex; justify-content: flex-end; margin-bottom: 5px; }
.btn-clear { background: none; border: none; color: #d9534f; cursor: pointer; font-size: 0.8rem; text-decoration: underline; padding: 0; }

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s ease-in-out infinite;
  vertical-align: middle; /* Aligns spinner with text baseline if needed */
  margin-right: 8px;
  position: relative;
  top: -1px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-upload.is-loading {
  pointer-events: none;
  opacity: 0.8;
}

.page-container.is-global-loading,
.page-container.is-global-loading * {
  cursor: wait !important;
}

/* --- POINTS LIST --- */
.points-list table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 15px; }
.points-list th { text-align: left; padding: 4px; color: #555; }
.points-list td { padding: 4px; border-bottom: 1px solid #eee; }
.coord-input { width: 70px; padding: 4px; font-size: 0.85rem; border: 1px solid #ddd; border-radius: 3px; }
.btn-remove { border: none; background: transparent; color: #999; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; padding: 4px; border-radius: 4px; transition: all 0.2s ease; }
.btn-remove:hover { color: #dc3545; background-color: rgba(220, 53, 69, 0.1); }

/* --- MAP LEGEND --- */
.map-legend {
  position: absolute; bottom: 30px; right: 340px; z-index: 999;
  background: rgba(255, 255, 255, 0.95); padding: 12px 15px; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2); width: 240px; font-family: sans-serif; pointer-events: none;
}

.legend-container {
  position: absolute;
  bottom: 30px;
  left: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column; /* This ensures they stack */
  align-items: flex-start;
  gap: 5px; /* Space between the two legends */
  pointer-events: none; /* Allow clicks to pass through empty space */
}

.scalar-legend-group {
  margin-bottom: 5px;
}

.legend-separator {
  height: 1px;
  background-color: #ddd;
  margin: 1px 0;
  width: 100%;
}

/* Vector Section Layout */
.vector-legend-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.vector-row {
  display: flex;
  align-items: center;
  gap: 4px; /* Space between arrow tip and text */
  margin-top: 0px;
}

.vector-label {
  font-size: 0.75rem;
  color: #444;
  font-weight: 600;
  white-space: nowrap;
  margin-bottom: 1px;
}

/* Ensure the SVG handles overflow correctly */
.vector-arrow-svg {
  display: block; /* Removes weird inline spacing */
  overflow: visible;
}

.legend-box {
  background: rgba(255, 255, 255, 0.95);
  padding: 3px 6px 3px 3px;
  border-radius: 6px;
  box-shadow: 0 0 8px rgba(0,0,0,0.2);
  width: 180px;
  pointer-events: auto; /* Re-enable clicks on the box itself */
  font-family: sans-serif;
  backdrop-filter: blur(2px);
}

.map-legend-item {
  display: flex;
  align-items: center;
  flex-direction: row;
  margin-top: 5px;
  font-size: 0.75rem;
  color: #333;
  line-height: 1.2;
}

.map-legend-line {
  width: 20px;
  height: 3px;
  margin-right: 8px;
  border-radius: 1px;
}

.map-legend-label {
  font-size: 0.75rem;
  color: #333;
  font-weight: 600;       /* Semi-bold looks good here */
  white-space: nowrap;    /* Keeps text on one line */
}

@media (max-width: 600px) {
  /* On phones, move legend to top-right or squash it further */
  .legend-container {
    bottom: 25px; 
    left: 5px;
    gap: 5px;
  }

  .legend-box {
    width: 140px; /* Even smaller width */
    padding: 6px 8px;
  }
  
  .map-legend-item {
    font-size: 0.7rem; 
  }
  
  .vector-label {
    font-size: 0.65rem;
  }
  
  /* Hide the scalar gradient bar if it's too big, or make it smaller */
  .legend-bar {
    height: 12px;
  }
}

/* --- SCALE BAR --- */
:deep(.leaflet-control-scale-line) {
  /* 1. Semi-transparent white background */
  background: rgba(255, 255, 255, 0.7) !important;
  
  /* 2. Black Borders */
  border-color: black !important;
  border-width: 2px !important;
  
  /* 3. Text Styling */
  color: black !important;
  font-weight: bold;
  font-size: 12px;
  
  /* Optional: Adjust padding for a cleaner look */
  padding: 2px 5px 0 5px !important;
  
  /* Ensure the 'ticks' (side borders) are visible */
  border-top: none !important;
  line-height: 1.1;
}

/* --- GLACIER LABELS --- */
/* We target the class defined in the JS options above */
:deep(.glacier-label) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-size: 10px; /* Small font to reduce clutter */
  font-weight: bold;
  color: #333;
  text-align: center;
  /* Add a white halo so text is readable on dark/complex backgrounds */
  text-shadow: 
    -1px -1px 0 #fff,  
     1px -1px 0 #fff,
    -1px  1px 0 #fff,
     1px  1px 0 #fff;
  
  /* Hide by default (opacity allows for smooth transition) */
  opacity: 0 !important;
  visibility: hidden;
  transition: opacity 0.3s ease;
  pointer-events: none; /* Let clicks pass through to the polygon/map */
}

/* Only show when the parent map-wrapper has the 'show-labels' class */
.show-labels :deep(.glacier-label) {
  opacity: 1 !important;
  visibility: visible;
}

/* HEADERS */
.map-legend h4,
.legend-box h4 {
  margin: 0px 0px 1px 2px !important;
  padding: 0 !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  color: #333;
  line-height: 1.1 !important;
  text-align: center;
}

/* BAR STYLING */
.legend-bar {
  height: 10px;
  width: 100%;
  border: 1px solid #ccc;
  margin-bottom: 1px;
}

.legend-bar-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 3px;
  font-size: 0.65rem;
  color: #666;
}

.legend-bar-labels-dynamic {
  position: relative;
  height: 15px; /* Ensures the container takes up space even with absolute children */
  margin-top: 3px;
  font-size: 0.65rem;
  color: #666;
}
.legend-bar-labels-dynamic span {
  position: absolute;
  top: 0;
}
.label-min { left: 0; }
.label-max { right: 0; }
.label-zero { transform: translateX(-50%); } /* translateX perfectly centers the "0" under the percentage point */

/* LEGEND GRADIENTS */
.viridis-gradient {
  background: linear-gradient(to right, #440154, #482878, #3e4989, #31688e, #26828e, #1f9e89, #35b779, #6ece58, #b5de2b, #fde725);
}
/* OLD BWR MAP .trend-gradient { background: linear-gradient(to right, #0000FF 0%, #4040FF 12.5%, #8080FF 25%, #BFBFFF 37.5%, #FFFFFF 50%, #FFBFBF 62.5%, #FF8080 75%, #FF4040 87.5%, #FF0000 100%); } */
.trend-gradient {
  background: linear-gradient(to right, #011261 0%, #024481 12.5%, #2E7CA6 25%, #92BDD2 37.5%, #EBEDEA 50%, #D4C096 62.5%, #AF8A3E 75%, #864C01 87.5%, #611200 100%);
}
.magma-gradient {
  background: linear-gradient(to right, #000004 0%, #180F3D 12.5%, #440F76 25%, #721F81 37.5%, #9C2E7F 50%, #CD4071 62.5%, #F1605D 75%, #FD9668 87.5%, #FCFDBF 100%);
}
.speed-gradient {
  /* Complex gradient from previous step */
  background: linear-gradient(to right, 
    #FFFFFF 0.22%, #FFFFFF 14.9%, #FDFFFF 16.0%, #E4FFFE 20.5%, #D7FFFE 24.0%, #D7FFFE 45.4%,
    #D1FBFB 46.6%, #70BACE 50%, #308FB1 52.2%, #03719C 54.5%, #03719C 61.3%, #167798 62.4%, 
    #548B8A 64.7%, #939E7D 66.9%, #D1B26F 69.2%, #C75D0F 76.0%, #D42C01 80.5%, #E20000 85.0%, 
    #C50000 87.3%, #990000 90.7%, #6F0000 95.2%, #4C0100 99.7%
  );
}
.batlow-gradient {
  background: linear-gradient(to right, #011959 0%, #19465B 12.5%, #35675A 25%, #578356 37.5%, #809C51 50%, #AEAE54 62.5%, #D5B966 75%, #EFC188 87.5%, #F9D3B5 100%);
}


/* --- CHART --- */
.axis-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  padding: 8px;
  background: #f8f9fa;
  border-top: 1px solid #ddd;
  font-size: 0.85rem;
  position: relative; 
  z-index: 10;
  flex-shrink: 0; 
}

.axis-group {
  display: flex;
  align-items: center;
  gap: 5px;
}

.axis-group label {
  font-weight: 600;
  color: #555;
  margin-right: 2px;
}

.axis-group input {
  width: 70px;
  padding: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
  text-align: center;
  font-size: 0.85rem;
}

.axis-group input[type="date"] {
    min-width: 110px; 
    padding: 4px;
    font-family: inherit;
}

.btn-reset-axes {
  background: white;
  border: 1px solid #aaa;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  color: #333;
}

.btn-reset-axes:hover {
  background: #eee;
  color: #d9534f;
  border-color: #d9534f;
}

.btn-icon {
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 6px;
  cursor: pointer;
  color: #555;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #f0f0f0;
  color: #000;
}

.btn-icon.active {
  background: #e6f7ff; 
  color: #1890ff;    
  border-color: #1890ff;
}

.trend-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trend-input {
  width: 85px;
  padding: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
  text-align: center;
  font-size: 0.85rem;
  background-color: #fffbe6; 
}

.inline-icon {
  display: inline-block;
  height: 3.0em;       /* Scales relative to the font size (makes it fit) */
  width: auto;         /* Maintains aspect ratio */
  vertical-align: middle; /* Aligns center of icon with center of lowercase text */
  margin: 0 0px;       /* Adds a tiny bit of breathing room */
  position: relative;  
  top: -2px;           /* visual tweak to lift it slightly if needed */
  fill: currentColor;  /* Optional: makes the icon take the text color */
}

/* CUSTOM LEGEND STYLES */
.custom-legend {
  display: flex;
  flex-wrap: wrap; 
  gap: 15px;       
  padding: 4px 10px 4px 65px;
  background: #fff;
  border-bottom: 1px solid #eee;
  min-height: 0px;
  justify-content: flex-start; 
  align-items: flex-start;
  position: relative;
  z-index: 20;
}

.legend-item {
  cursor: pointer;
  font-size: 0.85rem;
  user-select: none;
  display: flex;
  flex-direction: column; 
  align-items: flex-start;
  line-height: 1.2;
  gap: 0;
  transition: opacity 0.2s;
}

.legend-item:hover {
  opacity: 0.8;
}

/* Dim hidden items */
.legend-item.is-hidden {
  opacity: 0.4;
  text-decoration: line-through; 
}

.legend-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #333;
}

.legend-trend {
  font-weight: 400; /* Normal weight for stats */
  font-size: 0.8em; /* Slightly smaller */
  margin-top: -1px;
}

.legend-global-key {
  position: absolute;
  top: 100%; 
  left: 70px; 
  margin-top: 10px; 
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 15px;
  color: #555;
  font-size: 0.8rem;
  font-weight: 600;
  background: rgba(255,255,255,0.8); padding: 2px 5px; border-radius: 4px; 
  pointer-events: none; 
  z-index: 20;
}

.key-item {
  display: flex;
  align-items: center;
  gap: 6px; /* Space between the Symbol and the Word */
}

.key-separator {
  width: 1px;
  height: 20px;
  background: #ddd;
  margin-left: 5px;
}

.symbol-dot, .symbol-line, .symbol-dash {
  display: block;    
  flex-shrink: 0;    
}

.symbol-dot {
  width: 6px;
  height: 6px;
  background-color: #777;
  border-radius: 50%;
  border: 1px solid #777; /* Mimic the chart point style */
}

.symbol-line {
  width: 14px;
  height: 3px;
  background-color: #777;
  border-radius: 1px;
}

.symbol-dash {
  width: 14px;
  height: 0;
  border-top: 2px dashed #777;
}


/* --- FEEDBACK POPUP STYLES --- */
.feedback-popup {
  position: absolute;
  top: 50px; /* Adjust based on where your Layer Control sits */
  left: 70px;
  z-index: 9999; /* High z-index to sit above map tiles */
  background-color: white;
  padding: 12px 15px;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  gap: 10px;
  border-left: 4px solid #4CAF50; /* Nice green accent */
  max-width: 300px;
  font-family: 'Segoe UI', sans-serif;
  animation: slideIn 0.5s ease-out;
  cursor: default;
}

.feedback-content {
  font-size: 0.9rem;
  color: #333;
  line-height: 1.4;
}

.feedback-link {
  color: #2196F3;
  font-weight: 600;
  text-decoration: none;
}

.feedback-link:hover {
  text-decoration: underline;
}

.feedback-close {
  background: none;
  border: none;
  font-size: 1.5rem; /* Made slightly larger for visibility */
  color: #999;
  cursor: pointer;
  padding: 0 0 0 10px; /* added left padding for spacing */
  line-height: 0.8;    /* tighter line height centers the X better */
  font-family: Arial, sans-serif; /* Arial renders &times; reliably */
}

.feedback-close:hover {
  color: #333;
}


/* --- STATUS MESSAGE STYLES --- */
/* Container Position */
.status-toast {
  position: absolute;
  bottom: 30px;          /* Distance from bottom */
  left: 50%;
  transform: translateX(-50%); /* Center horizontally */
  z-index: 9999;         /* Ensure it's above the map */
  pointer-events: none;  /* Let clicks pass through to the map */
}

/* The Box Design */
.status-content {
  background: rgba(255, 255, 255, 0.9); /* Semi-transparent white */
  backdrop-filter: blur(4px);           /* Blur background behind it */
  padding: 10px 24px;
  border-radius: 50px;                  /* Pill shape */
  box-shadow: 0 4px 15px rgba(0,0,0,0.15);
  
  color: #333;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Optional: Simple CSS Spinner */
.message-display-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #ddd;
  border-top-color: #333; /* Dark spinner */
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Vue Transition Effects */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 20px); /* Slide up/down slightly */
}

/* Animations */
@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Add a fade transition for the toast */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Use 'deep' selector because these classes are inside Leaflet's SVG overlay */
:deep(.draggable-feature) {
  cursor: move;
  pointer-events: auto; /* Ensures the rectangle captures mouse clicks */
  transition: stroke-width 0.1s;
}

:deep(.draggable-feature:hover) {
  stroke-width: 2px; /* Thicken the line slightly when hovering */
  stroke-opacity: 0.8;
}

:deep(.draggable-feature:active) {
  cursor: grabbing;
}

.map-interaction-blocker {
  position: absolute;
  inset: 0;
  z-index: 9000; /* Just below the status-toast */
  cursor: wait;
  pointer-events: auto; /* Captures clicks so map doesn't get them */
  transition: opacity 0.2s; 
  background: rgba(255, 255, 255, 0);
}


/* TUTORIAL */
.play-tutorial-btn {
  display: flex; align-items: center; gap: 8px;
  background: #0066cc; color: white; border: none;
  padding: 10px 15px; border-radius: 4px; font-weight: bold;
  cursor: pointer; margin-bottom: 15px; width: 100%;
}
.play-tutorial-btn:hover { background: #0052a3; }

.play-icon {
  flex-shrink: 0; /* Prevents the icon from squishing */
  margin-top: 2px; /* Slight optical adjustment for vertical centering */
}

</style>

<style>
/* LEAFLET OVERRIDES (Global Style)
   Force layer control to expand on hover instead of click 
*/
.leaflet-control-layers-base {
  display: none !important;
}
.leaflet-control-layers-separator {
  display: none !important;
}

.leaflet-control-layers {
  border: none !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}

.leaflet-control-layers:hover {
  padding: 3px 6px 3px 3px !important;
  background: #fff !important;
  color: #333 !important;
  box-shadow: 0 1px 5px rgba(0,0,0,0.4) !important;
  border-radius: 5px !important;
  max-width: 200px;
}
.leaflet-control-layers:hover .leaflet-control-layers-list { display: block !important; font-size: 0.7rem; margin-bottom: 0; }
.leaflet-control-layers:hover .leaflet-control-layers-toggle { display: none !important; }

.leaflet-control-layers:hover label {
  margin-bottom: 1px !important; 
  margin-top: 1px !important;
  line-height: 0.9 !important;   
  display: flex !important;      
  align-items: center;           
  min-height: auto !important;   
}

/* Targets the actual checkbox/radio button to remove its default spacing */
.leaflet-control-layers:hover input {
  margin: 0 2px 0 0 !important; 
  height: 12px; 
  width: 12px;
}

@media (max-width: 480px) {
  .leaflet-control-layers {
    margin-top: 50px !important; 
    margin-right: 5px !important;
  }
}

/* --- PLOTLY TOOLBAR OVERRIDES --- */

/* 1. Force the toolbar to the top-right corner */
.js-plotly-plot .plotly .modebar {
    position: absolute;
    top: 10px !important;      /* Pin to very top */
    right: 20px !important;    /* Pin to very right */
    left: auto !important;
    
    /* Optional: Add a background so lines don't show through if they go high */
    background: rgba(255, 255, 255, 0.8) !important; 
}

/* 2. (Optional) Adjust the spacing of the icons */
.js-plotly-plot .plotly .modebar-group {
    background: transparent !important;
    padding-top: 0px !important; /* Centers buttons vertically in the margin space */
}

/* --- GLACIER LABELS --- */
.glacier-name-tooltip, .basin-name-tooltip {
    display: none !important; 
    background: transparent;
    border: none;
    box-shadow: none;
    font-weight: bold;
    color: #333; /* Or white, depending on your basemap */
    text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white; /* Gives a nice halo effect */
}

/* 2. Show Peninsula names when zoom >= 9 */
.show-glacier-names .glacier-name-tooltip {
    display: block !important;
}

/* polygon styling */
.basin-polygon {
    cursor: crosshair !important; /* Changes the pointing finger to a cross */
}

.basin-polygon:focus {
    outline: none !important; /* Kills the weird browser rectangle on middle-click */
}

/* Fallback just in case the browser targets the Leaflet wrapper */
svg path.leaflet-interactive:focus {
    outline: none !important; 
}

/* Styling for basin names on hover */
.basin-hover-tooltip {
    display: none !important;
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid #708090;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: bold;
    color: #333;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    pointer-events: none; 
}

/* Only show the tooltip if the map is zoomed in enough */
.show-basin-names .basin-hover-tooltip {
    display: block !important;
}

/* Styling for permanent IMBIE basin names (visible at all zoom levels) */
.imbie-basin-tooltip {
    background: transparent;
    border: none;
    box-shadow: none;
    font-weight: bold;
    color: #333; 
    text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;
}

/* 3. Show Antarctic Basins when 4 <= zoom < 9 */
/* .show-ant-basin-names .basin-name-tooltip {
    display: block !important;
}
*/

/* 4. Show Greenland Basins when zoom >= 5 */
/* .show-gr-basin-names .basin-name-tooltip {
    display: block !important;
}
*/

</style>