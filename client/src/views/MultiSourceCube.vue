<template>
  <div class="page-container" :class="{ 'is-global-loading': isUploading  }">
    
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
        :use-global-leaflet="true" 
		:options="mapOptions"
		@ready="onMapReady"
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
		  <div class="shiver-subtitle">Data Cube Extractor</div>
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
	  
	  
	  <div class="map-sidebar">
			  <button class="tool-btn" :class="{ 'is-active': isDrawing }" @click="startDrawing">
				<svg viewBox="0 0 24 24" class="icon"><path d="M12,21L4.35,16.5V7.5L12,3L19.65,7.5V16.5L12,21M12,4.3L6.1,7.7V15.3L12,18.7L17.9,15.3V7.7L12,4.3Z" /></svg>
				<span>{{ isDrawing ? 'Cancel' : 'Start' }}</span>
			  </button>

			  <button 
				class="tool-btn" 
				:class="{ 'is-active': isEditing && !isDrawing }" 
				:disabled="!isRegionDrawn || isUploadedShape"
				@click="toggleEdit"
			  >
				<svg viewBox="0 0 24 24" class="icon"><path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" /></svg>
				<span>Edit</span>
			  </button>

			  <button class="tool-btn" @click="undoLastPoint" :disabled="verticesHistory.length === 0">
				<svg viewBox="0 0 24 24" class="icon"><path d="M12.5,8C9.85,8 7.45,9 5.6,10.6L2,7V16H11L7.38,12.38C8.77,11.22 10.54,10.5 12.5,10.5C16.04,10.5 19.05,12.81 20.1,16L22.47,15.22C21.08,11.03 17.15,8 12.5,8Z" /></svg>
				<span>Undo</span>
			  </button>

			  <button class="tool-btn danger-btn" @click="resetDrawing" :disabled="!isRegionDrawn">
				<svg viewBox="0 0 24 24" class="icon"><path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19V4M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z" /></svg>
				<span>Delete</span>
			  </button>
			  
			  <button class="tool-btn success-btn" :class="{ 'ready-to-finish': (vertices.length >= 3 && isDrawing) || isEditing }" @click="finishDrawing" :disabled="!isDrawing && !isEditing">
				<svg viewBox="0 0 24 24" class="icon"><path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" /></svg>
				<span>Finish</span>
			  </button>
	  </div>
	  
	  
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
				  <h4>Percentage Valid Measurements</h4>
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
			  class="panel-btn" 
			  :class="{ 'active': currentRegion === 'Greenland' }"
			  @click="currentRegion = 'Greenland'; switchRegion()"
			  title="Switch to Greenland"
			>
			  <greenlandIcon class="btn-icon-svg" />
			</button>

			<button 
			  class="panel-btn" 
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
				  class="panel-btn" 
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
				  class="panel-btn" 
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
				
				<button class="panel-btn" @click="showHelp = true" title="Help">
				  <span><strong>?</strong></span>
				</button>
			  </div>
			  
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
	
	
	
	<div class="resize-handle" @mousedown.prevent="startDrag" @touchstart.prevent="startDrag">
       <div class="handle-grip"></div>
    </div>

	<div class="cube-controls" :style="{ height: (100 - mapHeightPercent) + '%' }">
    
		<div class="controls-header">
		  <div class="header-content">
			<h3><span class="icon">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
					<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84a.484.484 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.488.488 0 0 0-.59.22L2.09 8.83a.488.488 0 0 0 .12.61l2.03 1.58c-.05.3-.07.63-.07.94s.02.64.07.94l-2.03 1.58a.488.488 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.27.41.48.41h3.84c.24 0 .44-.17.48-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.488.488 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
				</svg>
			</span> Cube Configuration</h3>
			<p class="instruction">Draw a region on the map and select parameters.</p>
		  </div>
		</div>

		<div class="controls-body">
		
			<div class="control-card">
				<label class="section-label">Time Period</label>
				<div class="date-row">
					<div class="input-group">
						<span class="sub-label">Start</span>
						<input type="date" v-model="startDate" class="dark-input">
					</div>
					<div class="input-group">
						<span class="sub-label">End</span>
						<input type="date" v-model="endDate" class="dark-input">
					</div>
				</div>
			</div>

			<div class="control-card">
				    <label class="section-label">Variables</label>
					<div class="checkbox-scroller">
						<div class="checkbox-grid">
							<label v-for="v in availableVariables" :key="v.id" class="checkbox-item" :class="{ 'checked': selectedVariables.includes(v.id) }">
								<input type="checkbox" :value="v.id" v-model="selectedVariables" hidden>
								<span class="custom-check"></span>
								<span class="var-name">{{ v.name }}</span>
							</label>
						</div>
					</div>
			</div>

			<div class="control-card">
					<div style="display: flex; justify-content: space-between; align-items: center;">
						<label class="section-label">Data Sources</label>
						<div style="margin-bottom: 5px;">
							<button class="bulk-btn" @click="selectAllSources" style="margin-right: 5px; font-size: 0.8em;">All</button>
							<button class="bulk-btn" @click="unselectAllSources" style="font-size: 0.8em;">None</button>
						</div>
					</div>
					<div class="checkbox-scroller">
						<div class="checkbox-grid">
							<label v-for="s in availableSources" :key="s" class="checkbox-item" :class="{ 'checked': pendingSources.includes(s) }">
								<input type="checkbox" :value="s" v-model="pendingSources" hidden>
								<span class="custom-check"></span>
								<span class="var-name">{{ formatSourceName(s) }}</span>
							</label>
						</div>
					</div>
			</div>

		  <div class="control-card action-card">
			<div class="status-area">
			
				<div v-if="!isRegionDrawn" class="status-msg warning">
				   Upload file or draw a region on the map
				</div>
				
				<div v-else-if="!estimatedSize.valid" class="status-msg error">
					<span style="color: #f44336;" v-html="'' + estimatedSize.msg"></span>
				</div>

				<div v-else class="status-msg ready">
					<span>Selected Area:</span>
					<strong style="color: #4caf50;">{{ estimatedSize.areaSqKm.toFixed(0) }} km&sup2;</strong>
				</div>
			</div>
			
			<button 
			  class="modern-btn" 
			  @click="downloadCube" 
			  :disabled="!isReady || isDownloading || !estimatedSize.valid"
			  :class="{ 'btn-loading': isDownloading }"
			>
			  <span v-if="isDownloading" class="spinner-small"></span>
			  <span v-else>Request Data Cube via Email</span>
			</button>
		  </div>

		</div>
	  </div>
	
  </div>
  
  <div v-if="showHelp" class="modal-overlay" @click.self="showHelp = false">
      <div class="modal-content">
        <button class="modal-close" @click="showHelp = false">&times;</button>
        
        <h2>How to use SHIVER - Data Cube Extractor</h2>
	    <p>This gives a brief overview of the SHIVER Data Cube Extractor. Take a look at our <AppLink to="/documentation" class="text-link"><strong>SHIVER documentation</strong></AppLink> pages for more details.</p>
		
		<p>Or play the video tutorial below to see all of the SHIVER Data Cube Extractor functions</p>
		
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
		</div>
        
        <div class="modal-body">
          <h3>1. Basic Usage</h3>
		    <ul>
				<li>Navigate to your preferred ice sheet by clicking the Greenland button (<greenlandIcon class="inline-icon"/>)
						or the Antarctica button (<antarcticaIcon class="inline-icon"/>)</li>
				<li>Draw a polygon and choose a time-period to extract a data cube. Only one polygon can be drawn at a time.</li>
		    </ul>
			<p><strong>Note: Due to server constraints, only five data cube downloads per day per user are permitted.</strong></p>
			
		<h3>1. Advanced Usage</h3>
		    <ul>
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
				<li>Choose which data sources and variables to extract.</li>
		    </ul>
	
        </div>
      </div>
    </div>
	
	<VideoModal 
    :isOpen="isVideoModalOpen"
    title="SHIVER Data Cube Extractor Tutorial"
    :videoSrc="tutorialVideoSrc"
    @close="isVideoModalOpen = false"
  />
	
</template>

<script setup>
// --- IMPORTS ---
import { ref, shallowRef, computed, nextTick, watch, onMounted, onUnmounted, inject, markRaw } from 'vue';
import "leaflet/dist/leaflet.css";
import { LMap, LWmsTileLayer, LTileLayer, LGeoJson, LControlLayers, LLayerGroup, LControlScale, LTooltip } from "@vue-leaflet/vue-leaflet";
import axios from 'axios';
import { saveAs } from 'file-saver';
//import L from 'leaflet';
const L = shallowRef(null);
import antarcticaIcon from '../components/icons/antarcticaIcon.vue';
import greenlandIcon from '../components/icons/greenlandIcon.vue';
import * as turf from '@turf/turf';
import { differenceInWeeks, differenceInMonths, differenceInYears } from 'date-fns'; // useful for time steps
import { useAuthStore } from '../stores/auth';
import shp from 'shpjs';
import toGeoJSON from '@mapbox/togeojson'; // For KML
import JSZip from 'jszip'; // For KMZ
import VideoModal from '../components/VideoModal.vue';
const isVideoModalOpen = ref(false);
import { useHead } from '@unhead/vue'
const tutorialVideoSrc = ref('https://youtube.com/embed/Gbv7x24S7cU?si=_AP8s2pij1e84fIl');

// -----------------------------------------------------------------------------------------
// --- API CONFIGURATION --------------------------------------------------------------------
import apiClient, { API_URL } from '../api';


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

// -----------------------------------------------------------------------------------------
// --- SEO ---------------------------------------------------------------------------------
useHead({
  title: 'SHIVER | Interactive Data Cube Extractor',
  meta: [
    { 
      name: 'description', 
      content: 'Generate custom NetCDF files of ice velocity data compiled from multiple Earth Observations missions for the Greenland Ice Sheet and Antarctic Ice Sheet for any region and time period.' 
    }
  ]
})


// -----------------------------------------------------------------------------------------
// --- PROJ4 SETUP -------------------------------------------------------------------------
import proj4 from 'proj4';
//window.proj4 = proj4; // Crucial: proj4leaflet expects proj4 to be globally available in Vite!
//import 'proj4leaflet';
const crsGreenland = shallowRef(null)
const crsAntarctica = shallowRef(null)
const isMapReady = ref(false)

// Load proj4
onMounted(async () => {
  await nextTick();
  
  // 1. Dynamically import Leaflet
  const leafletModule = await import('leaflet');
  L.value = leafletModule.default || leafletModule;

  // 2. Now that we are safely in the browser, attach proj4 to the window
  window.proj4 = proj4;

  // 3. Dynamically import proj4leaflet ONLY AFTER Leaflet and window.proj4 are ready
  await import('proj4leaflet');
  
  // 4. Define CRS
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

  // Flip the switch to let the template render the map elements safely
  isMapReady.value = true;
  
  // Wait one tick for Vue to actually mount the map elements to the DOM 
  // before we try to read URL parameters and call `.setView()`
  await nextTick();

});

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


// --- REGION MANAGEMENT --- //
const switchRegion = () => {  
  if (currentRegion.value === 'Greenland') {
    center.value = [71.394,-40.987]; zoom.value = 1; // 67.133129, -48.900752
  } else {
    center.value = [-87.82, 87.09]; zoom.value = 0; // -66.323903, -63.355695
  }
  
  // Force Leaflet to fly to the new center
  if (map.value && map.value.leafletObject) map.value.leafletObject.setView(center.value, zoom.value);
};


// -----------------------------------------------------------------------------------------


// --- NATIVE GOOGLE ANALYTICS TRACKING ---
const trackEvent = (eventName, params = {}) => {
  // Check if window exists FIRST, then check for gtag
  if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
    window.gtag('event', eventName, params);
    console.log(`GA Event Sent: ${eventName}`, params);
  } else {
    console.log(`GA Event Skipped (Not loaded or server-side): ${eventName}`);
  }
};


// --- FEEDBACK POPUP STATE ---------------------------------------------------------------------
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
// -----------------------------------------------------------------------------------------



// --- REACTIVE STATE ---------------------------------------------------------------------
const map = shallowRef(null);
const currentRegion = ref('Greenland');
const zoom = ref(1);
const center = ref([71.394, -40.987]);
const statusMessage = ref("");
const statusType = ref("");
const isDragging = ref(false);
const isUploading = ref(false);
const showHelp = ref(false); 
const iceEdgeData = ref(null);
const groundingLineData = ref(null);
const mapHeightPercent = ref(70); 
const legendItems = ref([]);
const isUserZoomed = ref(false);
const TIME_DELAY_MS = 90000; // 1.5 Minutes 
const STORAGE_KEY = 'shiver_feedback_shown';
const showFeedbackPopup = ref(false);
const isMessageSpinnerRequired = ref(false);  // Optional: controls the spinner
const geoUpdateTrigger = ref(0);
const fileInput = ref(null);
const isDownloading = ref(false);
const auth = useAuthStore();
let leafletMap = null;
let timerInstance = null;
let messageTimeout = null;
// -----------------------------------------------------------------------------------------


// -----------------------------------------------------------------------------------------
// --- OVERLAY LAYERS // ---------------------------------------------------------------------
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


// COMPUTED URLs FOR TILES
const timestamp = computed(() => Date.now()); 
const baseUrl = API_URL.replace(/\/$/, '');
const wmsOverlayUrl = computed(() => `${baseUrl}/api/wms/${currentRegion.value}?t=${timestamp.value}`);
const wmsLandsatUrl = computed(() => `${baseUrl}/api/wms/${currentRegion.value}?t=${timestamp.value}`);
const wmsVectorUrl = computed(() => `${baseUrl}/api/wms/${currentRegion.value}/vectors`);

// ICE MARGIN
const iceEdgeStyle = { color: "black", weight: 2 };
const groundingLineStyle = { color: "magenta", weight: 2 };
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

// Legend labels (static)
const maxTrendLabel = computed(() => currentRegion.value === 'Greenland' ? '2.5' : '15');
const minTrendLabel = computed(() => currentRegion.value === 'Greenland' ? '-2.5' : '-15');
const maxCountLabel = computed(() => currentRegion.value === 'Greenland' ? '750' : '200');
// -----------------------------------------------------------------------------------------

// ---------------------------------------------------------------------------------------------
// --- ANALYSIS LAYERS --- // ---------------------------------------------------------------------
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
    
    console.log(`Loaded ${allEpochs.value.length} epochs for ${currentRegion.value}`);
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
// -----------------------------------------------------------------------------------------


// -----------------------------------------------------------------------------------------
// --- GLACIER BASINS ------------------------------------------------------------------------
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
// -----------------------------------------------------------------------------------------


// -----------------------------------------------------------------------------------------
// --- GLACIER LABELS -------------------------------------------------------------------------
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


// -----------------------------------------------------------------------------------------
// -- MULTI ZARR --- // -----------------------------------------------------------------------
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
// -----------------------------------------------------------------------------------------



// -----------------------------------------------------------------------------------------
// --- CUBE PARAMETERS --- //  ---------------------------------------------------------------------
const startDate = ref('2018-01-01');
const endDate = ref('2018-12-31');
const frequency = ref('monthly');
const selectedVariables = ref(['speed']);

// Cube limits
const MAX_AREA_SQKM = 15000; // sq km
const MAX_DAYS = 366;

const availableVariables = [
  { id: 'speed', name: 'Speed' },
  { id: 'vx', name: 'Easting velocity' },
  { id: 'vy', name: 'Northing velocity' },
];

// Computed parameters
const isReady = computed(() => {
    if (!isRegionDrawn.value) return false;
	return selectedVariables.value.length > 0 && pendingSources.value.length > 0;
});



// -----------------------------------------------------------------------------------------
// --- POLYGON DRAWING --- // -------------------------------------------------------------------
const isDrawing = ref(false);
const isEditing = ref(false);
const vertices = ref([]); // Only used to trigger Vue buttons (Start, Finish, etc.)
const verticesHistory = shallowRef([]);

// Pure JS variables - Vue Proxies cannot touch these!
let rawVertices = []; 
let markers = []; 
let midpoints = []; 
let visualPolygon = null; 
let ghostMarker = null;
let mouseTooltip = null; 
const drawnLayer = shallowRef(null);

const isRegionDrawn = computed(() => {
  // 1. Check if a file upload layer is currently on the map
  if (drawnLayer.value) return true;

  // 2. Fallback to checking manual drawing state
  return vertices.value.length >= 3 && !isDrawing.value;
});

const onMapReady = (mapInstance) => {
  leafletMap = mapInstance.leafletObject || mapInstance;
};

// --- 1. CORE DRAWING LOGIC ---
const addVertex = (lat, lng, index = null) => {
  saveHistoryState();
  // Update the pure JS array
  if (index === null) {
    rawVertices.push([lat, lng]);
  } else {
    rawVertices.splice(index, 0, [lat, lng]);
  }
  
  // Sync a clone to Vue so the buttons update, keeping the proxy away from Leaflet
  vertices.value = [...rawVertices]; 
  
  updatePolygonOnly();
  refreshMarkers();
};

// Save vertex history
const saveHistoryState = () => {
  verticesHistory.value = [...verticesHistory.value, JSON.parse(JSON.stringify(rawVertices))];
};

const handleMouseMove = (e) => {
  if (!isDrawing.value || !e.latlng) return;

  // 1. Ghost Marker (Kept because it works and looks good!)
  if (!ghostMarker) {
    const icon = L.value.divIcon({ className: 'vertex-handle ghost', iconSize: [12, 12], iconAnchor: [6, 6] });
    ghostMarker = L.value.marker([e.latlng.lat, e.latlng.lng], { icon, interactive: false, keyboard: false, zIndexOffset: 2000 }).addTo(leafletMap);
  } else {
    ghostMarker.setLatLng([e.latlng.lat, e.latlng.lng]);
  }

  // 2. Tooltip (Kept because it's helpful!)
  if (!mouseTooltip) {
    mouseTooltip = L.value.tooltip({ permanent: true, direction: 'right', className: 'drawing-cursor-tooltip', offset: [15, 0] })
      .setLatLng([e.latlng.lat, e.latlng.lng])
      .addTo(leafletMap);
  } else {
    mouseTooltip.setLatLng([e.latlng.lat, e.latlng.lng]);
  }

  const count = rawVertices.length;
  if (count === 0) {
    mouseTooltip.setContent("Click to start drawing");
  } else {
    mouseTooltip.setContent(count >= 3 ? "Click to add point or 'Finish'" : "Click to add point");
  }

};

const updatePolygonOnly = () => {
  if (rawVertices.length < 2) return;
  
  // Force explicit L.latLng objects for the main Polygon too
  const latLngs = rawVertices.map(v => L.value.latLng(v[0], v[1]));
  
  const style = { color: '#ffeb3b', weight: 3, fillOpacity: 0.2, dashArray: isDrawing.value ? '10, 10' : null, interactive: false };

  if (!visualPolygon) {
    visualPolygon = L.value.polygon(latLngs, style).addTo(leafletMap);
  } else {
    visualPolygon.setLatLngs(latLngs);
    visualPolygon.setStyle(style);
  }

  if (rawVertices.length >= 3) {
    const geojson = visualPolygon.toGeoJSON();
    const areaSqKm = (turf.area(geojson) / 1e6).toFixed(0);
    visualPolygon.unbindTooltip();
    visualPolygon.bindTooltip(`${areaSqKm} km&sup2`, { permanent: true, direction: 'center', className: 'area-tooltip-internal' }).openTooltip();
	
	// Update the computed size
	geoUpdateTrigger.value++;
  }
};

// --- 2. MARKERS & INTERACTION ---
const clearMarkers = () => {
  markers.forEach(m => leafletMap.removeLayer(m));
  midpoints.forEach(m => leafletMap.removeLayer(m));
  markers = [];
  midpoints = [];
};

const createMarker = (latlng, isMidpoint = false, index = null) => {
  const icon = L.value.divIcon({
    className: isMidpoint ? 'midpoint-handle' : 'vertex-handle',
    iconSize: isMidpoint ? [10, 10] : [14, 14],
    iconAnchor: isMidpoint ? [5, 5] : [7, 7]
  });

  const marker = L.value.marker(latlng, { 
    icon, 
    draggable: !isMidpoint, 
    zIndexOffset: isMidpoint ? 1000 : 2000,
    keyboard: false 
  }).addTo(leafletMap);

  if (isMidpoint) {
    marker.on('click', (e) => {
      L.value.DomEvent.stopPropagation(e);
      addVertex(latlng[0], latlng[1], index);
    });
  } else {
    marker.on('dragstart', () => {
      if (leafletMap.dragging) leafletMap.dragging.disable();
	  saveHistoryState();
    });
    
    marker.on('drag', (e) => {
      const i = markers.indexOf(marker);
      if (i > -1) {
        const newPos = e.target.getLatLng();
        rawVertices[i] = [newPos.lat, newPos.lng];
        updatePolygonOnly(); 
        updateMidpointsPosition(); 
      }
    });
    
    marker.on('dragend', () => {
      if (leafletMap.dragging) leafletMap.dragging.enable();
      vertices.value = [...rawVertices]; 
      refreshMarkers(); 
    });
  }
  return marker;
};

const refreshMarkers = () => {
  clearMarkers();
  if (!isDrawing.value && !isEditing.value) return;
  rawVertices.forEach((v) => markers.push(createMarker(v, false)));
  if (rawVertices.length >= 2) {
    const count = rawVertices.length;
    for (let i = 0; i < count; i++) {
      if (isDrawing.value && i === count - 1) break;
      const p1 = rawVertices[i];
      const p2 = rawVertices[(i + 1) % count];
      midpoints.push(createMarker([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2], true, i + 1));
    }
  }
};

const updateMidpointsPosition = () => {
  const count = rawVertices.length;
  if (count < 2) return;
  let midIdx = 0;
  for (let i = 0; i < count; i++) {
    if (isDrawing.value && i === count - 1) break;
    const p1 = rawVertices[i];
    const p2 = rawVertices[(i + 1) % count];
    if (midpoints[midIdx]) {
      midpoints[midIdx].setLatLng([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]);
    }
    midIdx++;
  }
};


// --- 3. CONTROLS ---
const handleMapClick = (e) => {
  if (!isDrawing.value) return;
  addVertex(e.latlng.lat, e.latlng.lng);
  // Ghost line initialization is totally gone!
};

const startDrawing = () => {
  if (!leafletMap) return;
  if (isDrawing.value) {
    finishDrawing();
    return;
  }
  if (drawnLayer.value) {
    leafletMap.removeLayer(drawnLayer.value); 
    drawnLayer.value = null;
  }
  isUploadedShape.value = false;
  resetDrawing();
  isDrawing.value = true;
  leafletMap.on('click', handleMapClick);
  leafletMap.on('mousemove', handleMouseMove);
  leafletMap.getContainer().style.cursor = 'crosshair';
};

const finishDrawing = () => {
  isDrawing.value = false;
  isEditing.value = false;
  
  if (mouseTooltip) { leafletMap.removeLayer(mouseTooltip); mouseTooltip = null; }
  if (ghostMarker) { leafletMap.removeLayer(ghostMarker); ghostMarker = null; }
  
  leafletMap.off('click', handleMapClick);
  leafletMap.off('mousemove', handleMouseMove);
  leafletMap.getContainer().style.cursor = '';

  if (vertices.value.length >= 3) {
    drawnLayer.value = visualPolygon;
    updatePolygonOnly();
    refreshMarkers();
  } else {
    resetDrawing();
  }
};

const undoLastPoint = () => {
  if (verticesHistory.value.length === 0) return;

  // Pop the last snapshot and overwrite current vertices
  rawVertices = verticesHistory.value.pop();
  vertices.value = [...rawVertices];
  verticesHistory.value = [...verticesHistory.value];

  // If we undid our way back to an empty map, clean up the visual layer
  if (rawVertices.length === 0 && visualPolygon) {
    leafletMap.removeLayer(visualPolygon);
    visualPolygon = null;
    drawnLayer.value = null; // Important to reset this so estimatedSize clears
  } 
  
  updatePolygonOnly();
  refreshMarkers();
};

const toggleEdit = () => {
  isEditing.value = !isEditing.value;
  isDrawing.value = false;
  refreshMarkers();
};

const resetDrawing = () => {
  if (drawnLayer.value) {
    leafletMap.removeLayer(drawnLayer.value);
    drawnLayer.value = null;
  }
  isUploadedShape.value = false;
  isDrawing.value = false;
  isEditing.value = false;
  
  if (!leafletMap) {
    rawVertices = [];
    verticesHistory.value = []; 
    vertices.value = [];
    return;
  }

  clearMarkers();
  if (visualPolygon) leafletMap.removeLayer(visualPolygon);
  if (mouseTooltip) leafletMap.removeLayer(mouseTooltip);
  if (ghostMarker) leafletMap.removeLayer(ghostMarker);
  
  rawVertices = [];
  vertices.value = [];
  verticesHistory.value = []; 
  visualPolygon = null;
  mouseTooltip = null;
  ghostMarker = null;
  drawnLayer.value = null;
  
  leafletMap.off('click', handleMapClick);
  leafletMap.off('mousemove', handleMouseMove);
  leafletMap.getContainer().style.cursor = '';
};


// -----------------------------------------------------------------------------------------
// --- CUBE GENERATION --- // ----------------------------------------------------------------
const downloadCube = async () => {
  if (!drawnLayer.value) {
    setStatus('Error: Please draw a region first.', 'error');
    return;
  }

  isDownloading.value = true;
  setStatus('Processing request...', 'loading');

  try {
    const geojson = drawnLayer.value.toGeoJSON();
    const geometry = geojson.geometry ? geojson.geometry : geojson; // Handle Rectangle vs Polygon structure

	// Dynamic payload
    const payload = {
      roi_geojson: geometry,
      date_start: startDate.value,
      date_end: endDate.value,
      variables: selectedVariables.value,
	  sources: pendingSources.value
    };
	
	// Grab the token directly from sessionStorage
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('shiver_token') : null;

    // We request 'blob' because 90% of the time it will be a file.
    // If it is JSON (202 Accepted), we will convert the blob to text manually.
    const response = await apiClient.post('/api/multiSourceCube/download', payload, {
      responseType: 'blob', 
      headers: { 'Authorization': `Bearer ${token}` }
    });

    // --- CASE 1: LARGE FILE (Background Processing) ---
    if (response.status === 202) {
      // The response is a Blob containing JSON. Convert it to text.
      const textData = await response.data.text(); 
      const jsonData = JSON.parse(textData);
      setStatus('Request Accepted: Check your email.', 'success');
      return; // Stop here, do not try to download
    }

    // --- CASE 2: SMALL FILE (Direct Download) ---
    if (response.status === 200) {

        // 1. Robust Filename Extraction
        let filename = 'cube.nc'; // Fallback
        
        // Headers can be case-insensitive, so we check carefully
        const disposition = response.headers['content-disposition'];

        if (disposition && disposition.indexOf('attachment') !== -1) {
            // Regex to match filename="name" or filename=name
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) { 
                filename = matches[1].replace(/['"]/g, '');
            }
        }

        // 2. Create Download Blob
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        
        // 3. Use the extracted filename
        link.setAttribute('download', filename);
        
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        link.remove();
        window.URL.revokeObjectURL(url);
        
        setStatus(`Download Started: ${filename}`, 'success'); // Changed to 'success' (green)
    }

  } catch (error) {
    console.error(error);
    let msg = "Server Error";

    // Handle Blob Errors (since responseType was 'blob', errors are also blobs)
    if (error.response && error.response.data) {
        try {
            // Convert Blob error to text
            const text = await error.response.data.text();
            const json = JSON.parse(text);
            msg = json.detail || json.message;
        } catch(e) {
            // If parsing fails, use default message
        }
        
        // Handle 401 Unauthorized specifically
        if (error.response.status === 401) {
            msg = "Session expired. Please log in again.";
            auth.logout();
            router.push('/login');
        }
    }
    
    setStatus(`Error: ${msg}`, 'error');
  } finally {
    isDownloading.value = false;
  }
};

const setStatus = (msg, type) => {
  statusMessage.value = msg;
  statusType.value = type;
  
  // Clear message after 5 seconds unless it's a persistent state
  if (type !== 'loading' && type !== 'error') {
    setTimeout(() => {
        statusMessage.value = '';
        statusType.value = '';
    }, 5000);
  }
};
// -----------------------------------------------------------------------------------------



// -----------------------------------------------------------------------------------------
// --- CUBE SIZE ESTIMATION -------------------------------------------------------------------
const estimatedSize = computed(() => {
  geoUpdateTrigger.value; 
  
  const result = { areaSqKm: 0, valid: true, msg: '' };

  if (!drawnLayer.value || !startDate.value || !endDate.value) return result;

  try {
    // 1. Check Area
    const geojson = drawnLayer.value.toGeoJSON();
    const areaSqKm = turf.area(geojson) / 1e6;

    if (areaSqKm > MAX_AREA_SQKM) {
        return {
            areaSqKm, 
            valid: false, 
            msg: `Area too large (${areaSqKm.toFixed(0)} km&sup2;). Max is 15,000 km&sup2;.` 
        };
    }

    // 2. Check Time Period
    const start = new Date(startDate.value);
    const end = new Date(endDate.value);
    
    // Calculate difference in days
    const daysDiff = (end - start) / (1000 * 60 * 60 * 24);

    if (daysDiff < 0) {
        return { areaSqKm, valid: false, msg: `End date must be after start date.` };
    }
    
    if (daysDiff > MAX_DAYS) {
        return {
            areaSqKm,
            valid: false,
            msg: `Time period too long (${daysDiff.toFixed(0)} days). Max is 1 year.`
        };
    }

    // Success
    return { areaSqKm, valid: true, msg: 'Ready for extraction.' };

  } catch (e) {
    console.error(e);
    return { areaSqKm: 0, valid: false, msg: 'Calculation Error' };
  }
});

// Helper for UI Color
const sizeColor = computed(() => {
  // 1. If Invalid, show Red (Error color)
  if (!estimatedSize.value.valid) return '#f44336'; 

  // 2. Get the number
  const size = estimatedSize.value.sizeMB;

  // 3. Standard Logic
  if (size < 100) return '#4caf50'; // Green (Small)
  if (size < 500) return '#ffeb3b'; // Yellow (Medium)
  return '#f44336'; // Red (Large)
});



// -----------------------------------------------------------------------------------------
// --- FILE UPLOAD ---------------------------------------------------------------------------
const isUploadedShape = ref(false);
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  isUploading.value = true;
  setStatus('Parsing file...', 'loading');

  try {
    const fileName = file.name.toLowerCase();
    let geojson = null;

    // --- CASE A: GeoJSON ---
    if (fileName.endsWith('.geojson') || fileName.endsWith('.json')) {
      const text = await file.text();
      geojson = JSON.parse(text);
    } 
    // --- CASE B: Zipped Shapefile (.zip) ---
    else if (fileName.endsWith('.zip')) {
      const buffer = await file.arrayBuffer();
      geojson = await shp(buffer);
    } 
    // --- CASE C: KML (.kml) ---
    else if (fileName.endsWith('.kml')) {
      const text = await file.text();
      const parser = new DOMParser();
      const kmlDom = parser.parseFromString(text, 'text/xml');
      geojson = toGeoJSON.kml(kmlDom);
    } 
    // --- CASE D: KMZ (.kmz) ---
    else if (fileName.endsWith('.kmz')) {
      const buffer = await file.arrayBuffer();
      const zip = await JSZip.loadAsync(buffer);
      
      // Find the first .kml file inside the zip
      const kmlFile = Object.keys(zip.files).find(n => n.endsWith('.kml'));
      if (!kmlFile) throw new Error("No KML file found inside KMZ");
      
      const kmlString = await zip.file(kmlFile).async('string');
      const parser = new DOMParser();
      const kmlDom = parser.parseFromString(kmlString, 'text/xml');
      geojson = toGeoJSON.kml(kmlDom);
    } 
    else {
      throw new Error("Unsupported file format. Please use .zip (Shapefile), .geojson, .kml, or .kmz");
    }

    // --- VALIDATION & CLEANUP ---
    // Handle FeatureCollections (take the first feature) or Arrays
    if (Array.isArray(geojson)) {
      // shpjs sometimes returns an array of feature collections
      geojson = geojson[0]; 
    }
    
    // Normalize to a single feature if it's a FeatureCollection
    if (geojson.type === 'FeatureCollection') {
        if (geojson.features.length === 0) throw new Error("File contains no geometries.");
        // Merge or just take the first one? 
        // For simplicity, let's take the first feature, as requested.
        geojson = geojson.features[0];
    }

    // --- DRAW ON MAP ---
    drawGeoJSONOnMap(geojson);
	isUploadedShape.value = true;
    setStatus('File uploaded successfully', 'success');

  } catch (error) {
    console.error(error);
    setStatus(`Upload Failed: ${error.message}`, 'error');
  } finally {
    isUploading.value = false;
    // Reset the input so the same file can be selected again if needed
    event.target.value = ''; 
  }
};


// --- HELPER TO RENDER ON LEAFLET ---
const drawGeoJSONOnMap = (geojsonFeature) => {
  // Safety check: ensure map is loaded
  if (!leafletMap) {
      console.error("Map not ready yet.");
      return;
  }

  // A. Remove existing uploaded layer
  if (drawnLayer.value) {
    leafletMap.removeLayer(drawnLayer.value);
    drawnLayer.value = null;
  }
  
  // Reset Vue refs i.e. manually drawn layer
  vertices.value = [];
  isDrawing.value = false;
  isEditing.value = false;
  if (visualPolygon) {
    leafletMap.removeLayer(visualPolygon);
    visualPolygon = null;
  }
  if (ghostMarker) {
    leafletMap.removeLayer(ghostMarker);
    ghostMarker = null;
  }
  if (mouseTooltip) {
    leafletMap.removeLayer(mouseTooltip);
    mouseTooltip = null;
  }
  
  // Clean up drawing arrays
  markers.forEach(marker => leafletMap.removeLayer(marker));
  markers = [];
  midpoints.forEach(midpoint => leafletMap.removeLayer(midpoint));
  midpoints = [];
  rawVertices = [];

  // B. Parse the GeoJSON
  const tempLayer = L.value.geoJSON(geojsonFeature);
  const layers = tempLayer.getLayers();
  
  if (layers.length === 0) return;
  
  const newLayer = layers[0]; // Take the first shape found

  // C. Apply your specific Yellow Dashed Styling
  if (newLayer.setStyle) {
      newLayer.setStyle({ 
        color: '#ffeb3b', 
        weight: 2, 
        fillOpacity: 0.2, 
        dashArray: '5, 5' 
      });
  }

  // Calculate Area and Add Tooltip ---
  try {
      // We can use the geojsonFeature directly with Turf
      const areaSqKm = (turf.area(geojsonFeature) / 1e6).toFixed(0);
      
      newLayer.bindTooltip(`${areaSqKm} km&sup2;`, {
          permanent: true,
          direction: 'center',
          className: 'polygon-area-tooltip' 
      });
  } catch (err) {
      console.warn("Could not calculate area for uploaded shape.", err);
  }

  // D. Add to Map and Update State
  newLayer.addTo(leafletMap);
  newLayer.openTooltip(); // Ensure the tooltip opens after adding to map
  drawnLayer.value = newLayer;

  // E. Attach the 'remove' listener
  newLayer.on('remove', () => { 
      drawnLayer.value = null; 
  });
  
  // G. Fly to the new location
  leafletMap.fitBounds(newLayer.getBounds(), { padding: [50, 50] });
};



//--------------------------------------------------------------------------------------------
// --- WATCHER FOR STATUS MESSAGE --------------------------------------------------------------
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



//--------------------------------------------------------------------------------------------
// --- DRAG BAR -------------------------------------------------------------------------------
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


</script>
// -------------------------------------------------------------------------------------------------------
// ------------------ END OF SCRIPT ------------------------------------------------------------------------
// -------------------------------------------------------------------------------------------------------



<style scoped>
/* --- MAIN LAYOUT --- */
.page-container { display: flex; flex-direction: column; height: calc(100vh - 60px); width: 100%; overflow: hidden; }
.map-wrapper { position: relative; width: 100%; user-select: none; container-type: size; container-name: map-container }


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
  z-index: 2001; /* Sit on top of everything */
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
@container map-container (height < 300px) {
  
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
.cube-controls {
  background: #1a2634;
  color: #e0e6ed;
  padding: 0; /* Padding moved to inner elements for better scroll control */
  display: flex;
  flex-direction: column;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
  border-top: 1px solid #2c3e50;
  overflow: hidden; /* Prevent double scrollbars */
  transition: height 0.3s ease;
}

.controls-header {
  padding: 15px 25px;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid #2c3e50;
  flex-shrink: 0;
}

.controls-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #00ccff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.controls-header .instruction {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  color: #8b9bb4;
}

/* --- GRID LAYOUT FOR BODY --- */
.controls-body {
  padding: 20px 25px;
  overflow-y: auto; /* Allow scrolling inside controls if screen is short */
  display: grid;
  /* Magic Grid: Columns are at least 300px wide. 
     If space permits, they sit side-by-side (3 columns).
     If space is tight (tablet/mobile), they wrap automatically.
  */
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 25px;
  align-items: start;
}

/* --- CARDS (COLUMNS) --- */
.control-card {
  background: rgba(255,255,255,0.03);
  padding: 15px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.05);
  display: flex;
  flex-direction: column;
  height: 100%; /* Match height of neighbors */
  container-type: inline-size;
}

.section-label {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #8b9bb4;
  margin-bottom: 10px;
  font-weight: 700;
}

.mt-3 { margin-top: 15px; }

/* --- INPUTS --- */
.dark-input {
  background: #0b1e3b;
  border: 1px solid #2c3e50;
  color: white;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s ease;
  width: 100%;
  box-sizing: border-box; /* Fix padding issues */
}

.dark-input:focus {
  border-color: #00ccff;
  box-shadow: 0 0 0 2px rgba(0, 204, 255, 0.2);
}

.date-row {
  display: flex;
  align-items: flex-end; /* Align inputs */
  gap: 10px;
  flex-wrap: wrap;
}

.input-group {
  flex: 1 1 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
}

.sub-label {
  font-size: 0.75rem;
  color: #6c7a89;
}

.separator {
  padding-bottom: 10px;
  color: #8b9bb4;
  font-weight: bold;
}

@container (max-width: 320px) {
  .separator {
    display: none;
  }
  
  /* Optional: Add a tiny vertical gap when stacked so they don't touch */
  .date-row {
    gap: 8px; 
  }
}

/* --- CUSTOM CHECKBOXES --- */
.checkbox-scroller {
  max-height: 250px;
  overflow-y: auto;
  padding-right: 5px;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 6px;
  background: rgba(0,0,0,0.2);
  cursor: pointer;
  transition: background 0.2s;
}

.checkbox-item:hover {
  background: rgba(255,255,255,0.05);
}

.checkbox-item.checked {
  background: rgba(0, 204, 255, 0.1);
  border: 1px solid rgba(0, 204, 255, 0.3);
}

.custom-check {
  width: 16px;
  height: 16px;
  border: 2px solid #556;
  border-radius: 3px;
  display: inline-block;
  position: relative;
}

.checkbox-item.checked .custom-check {
  background: #00ccff;
  border-color: #00ccff;
}

/* Checkmark tick */
.checkbox-item.checked .custom-check::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 4px;
  height: 8px;
  border: solid #0b1e3b;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.var-name {
  font-size: 0.9rem;
  user-select: none;
}

/* --- ACTION AREA --- */
.action-card {
  justify-content: space-between;
  align-items: center;
  text-align: center;
  background: transparent; /* No bg for action card to look cleaner */
  border: none;
}

.status-area {
  margin-bottom: 15px;
  width: 100%;
}

.status-msg {
  padding: 10px;
  border-radius: 6px;
  font-size: 0.9rem;
}

.status-msg.warning {
  background: rgba(255, 235, 59, 0.1);
  color: #ffeb3b;
  border: 1px solid rgba(255, 235, 59, 0.3);
}

.status-msg.ready {
  background: rgba(0, 255, 150, 0.1);
  color: #00ff96;
  border: 1px solid rgba(0, 255, 150, 0.3);
  display: flex;
  flex-direction: column;
}

.modern-btn {
  background: linear-gradient(135deg, #00ccff 0%, #0088cc 100%);
  color: white;
  border: none;
  padding: 12px 30px;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 50px; /* Pill shape */
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 15px rgba(0, 204, 255, 0.3);
  width: 100%;
}

.modern-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 204, 255, 0.4);
}

.modern-btn:disabled {
  background: #2c3e50;
  color: #556;
  box-shadow: none;
  cursor: not-allowed;
}

/* --- MOBILE RESPONSIVENESS --- */
@media (max-width: 768px) {
  .cube-controls {
    /* IMPORTANT: On mobile, 35% height is too small to stack everything.
       We force it to be at least auto-height or fixed larger size.
       Using !important to override the inline style from Vue.
    */
    height: auto !important; 
    min-height: 50%; 
    max-height: 80%; /* Don't cover the whole map */
  }

  .controls-body {
    grid-template-columns: 1fr; /* Force single column stack */
    padding: 15px;
  }
  
  /* Make date inputs stack on very small screens */
  .date-row {
      flex-direction: row; 
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


/* --- GEOMAN --- */
.polygon-area-tooltip { background: rgba(0,0,0,0.7); color: white; border: none; font-weight: bold; }


/* Sidebar Container */
.map-sidebar {
  position: absolute;
  top: 160px;
  left: 20px;
  transform: translateY(-50%);
  z-index: 1000;
  
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2px; /* Tight stack */
  padding: 5px;
  background: rgba(40, 40, 40, 0.8);
  backdrop-filter: blur(8px);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.map-sidebar .tool-btn:last-child {
  grid-column: span 2;
}

.tool-btn {
  width: 100%;
  height: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #ccc;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 4px;
}

/* Icon Styling */
.tool-btn .icon {
  width: 24px;
  height: 24px;
  fill: currentColor;
  margin-bottom: 4px;
}

.tool-btn span {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Reactivity / Hover States */
.tool-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  transform: scale(1.05);
}

.tool-btn:active:not(:disabled) {
  transform: scale(0.95);
}

/* Active / Pressed State */
.tool-btn.is-active {
  background: #ffeb3b !important;
  color: #222 !important;
  box-shadow: inset 0 3px 5px rgba(0,0,0,0.4);
  font-weight: bold;
}

/* Disabled / Unreactive State */
.tool-btn:disabled {
  opacity: 0.2;
  filter: grayscale(1);
  cursor: not-allowed;
}

.ready-to-finish {
  background: rgba(76, 175, 80, 0.3);
  color: #4CAF50;
  animation: pulse 2s infinite;
}

/* Specific button colors when active */
.tool-btn.active { color: #ffeb3b; }
.success-btn:hover:not(:disabled) { color: #4CAF50 !important; }
.danger-btn:hover:not(:disabled) { color: #F44336 !important; }

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}


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

/* --- PAGE BEHAVIOUR --- */
.page-container.is-global-loading,
.page-container.is-global-loading * {
  cursor: wait !important;
}


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



/* --- OVERLAY MANAGER --- */
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


/*------------------------------------*/
/* --- POLYGON DRAWING --------------- */
/*------------------------------------*/
/* Marker Handles */
.vertex-handle {
  background: #fff;
  border: 2px solid #2196F3;
  border-radius: 50%;
  cursor: crosshair;
}

.vertex-handle.ghost {
  opacity: 0.6;
  pointer-events: none; /* Crucial so it doesn't block map clicks */
}

.midpoint-handle {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid #2196F3;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0.6;
}

.midpoint-handle:hover {
  opacity: 1;
  background: #2196F3;
}

/* Tooltips */
.drawing-cursor-tooltip {
  background: rgba(0, 0, 0, 0.7);
  border: none;
  color: white;
  font-weight: bold;
  pointer-events: none;
}

.area-tooltip-internal {
  background: rgba(255, 255, 0, 0.8);
  border: 1px solid #333;
  font-weight: bold;
  padding: 2px 5px;
}

</style>