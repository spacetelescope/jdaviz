<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#cubeviz-sonify-data'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to"
    :disabled_msg="disabled_msg">

    <j-plugin-section-header>Cube Pre-Sonification Options</j-plugin-section-header>
    <v-alert v-if="!has_strauss" type="warning" style="margin-left: -12px; margin-right: -12px">
      To use Sonify Data, install strauss and restart Jdaviz. You can do this by running pip install strauss
      in the command line and then launching Jdaviz.
    </v-alert>
    <v-row v-if="has_strauss && !has_outs">
      <j-docs-link>Sonification on platforms is under construction!</j-docs-link>
    </v-row>

    <v-row>
      <j-docs-link>Choose the input cube, spectral subset and any advanced sonification options.</j-docs-link>
    </v-row>
    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data set."
      :disabled="true"
    />
    <plugin-subset-select
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :show_if_single_entry="true"
      label="Spectral range"
      api_hint="plg.spectral_subset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select spectral region that defines the wavelength range."
    />
    <v-row>
      <v-expansion-panels accordion>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Advanced Sound Options</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <v-row>
              <v-text-field
                ref="audfrqmin"
                type="number"
                label="Minimum Audio Frequency"
                v-model.number="audfrqmin"
                hint="The minimum audio frequency used to represent the spectra (Hz)"
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="audfrqmax"
                type="number"
                label="Maximum Audio Frequency"
                v-model.number="audfrqmax"
                hint="The maximum audio frequency used to represent the spectra (Hz)"
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="assidx"
                type="number"
                label="Audio Spectrum Scaling Index"
                v-model.number="assidx"
                hint="The desired audio spectrum scaling index, typically > 1."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="ssvidx"
                type="number"
                label="Spectrum-Spectrum Volume Index"
                v-model.number="ssvidx"
                hint="The desired spectrum-spectrum volume index, typically [0,1]."
                persistent-hint
              ></v-text-field>
            </v-row>
	    <v-row>
              <v-switch
                v-model="use_pccut"
                label="Use Flux Percentile Cut?"
                hint="Whether to only sonify flux above a min. percentile (else use absolute values)"
                persistent-hint
               ></v-switch>
	    </v-row>
            <v-row v-if="use_pccut">
              <v-text-field
                ref="pccut"
                type="number"
                label="Flux Percentile Cut Value"
                v-model.number="pccut"
                hint="The minimum percentile to be heard."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
               <v-switch
                 v-model="eln"
                 label="Equal Loudness Equalisation"
                 hint="Whether to equalise for uniform perceived loudness"
                 persistent-hint
                ></v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>
    <j-plugin-section-header>Live Sound Options</j-plugin-section-header>
    <v-row>
      <plugin-action-button
        @click="refresh_device_list_in_dropdown"
      >
        Refresh Device List
      </plugin-action-button>
    </v-row>
    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="sound_devices_items"
        v-model="sound_devices_selected"
        label="Sound device"
        hint="Device which sound will be output from."
        persistent-hint
        ></v-select>
    </v-row>

    <v-row>
        Overall Volume
        <glue-throttled-slider label="Volume" wait="300" max="100" step="1" :value.sync="volume" hide-details class="no-hint" />
    </v-row>
    <j-plugin-section-header>Add Results Options</j-plugin-section-header>
      <plugin-add-results
          :label.sync="results_label"
          :label_default="results_label_default"
          :label_auto.sync="results_label_auto"
          :label_invalid_msg="results_label_invalid_msg"
          :label_overwrite="results_label_overwrite"
          label_hint="Label for the sonified data"
          :add_to_viewer_items="add_to_viewer_items"
          :add_to_viewer_selected.sync="add_to_viewer_selected"
          add_to_viewer_hint="Add sonified layer to selected viewer. The sonified data will be available to add to all relevant viewers after creation."
          action_label="Sonify data"
          action_tooltip="Create sonified data and add to selected viewer"
          :action_spinner="spinner"
          action_api_hint='plg.sonify_cube()'
          @click:action="handleSonifyClick"
      ></plugin-add-results>
 </j-tray-plugin>
</template>

<script>
// Tone.js is loaded dynamically in the mounted() hook
export default {
    data() {
	return {
            // Tone.js objects
            player1: null,
            player2: null,
            panner1: null,
            panner2: null,
            crossFade: null,
            activePlayer: 1, // 1 or 2
            isFading: false,
            lindxLatest: null,
            toneJsLoadPromise: null,
            loopDuration: null,
	}
    },
    mounted() {
	this.toneJsLoadPromise = new Promise((resolve, reject) => {
            if (window.Tone) {
		console.log('Tone.js already loaded.');
		console.log("Tone.context.lookAhead = ", Tone.context.lookAhead, "s");
		console.log("Tone.context.updateInterval = ", Tone.context.updateInterval, "s");
		return resolve();
            }
            console.log('Loading Tone.js...');
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.min.js';
            script.onload = () => {
		console.log('Tone.js loaded successfully.');
		console.log("Tone.context.lookAhead = ", Tone.context.lookAhead, "s");
		console.log("Tone.context.updateInterval = ", Tone.context.updateInterval, "s");
		resolve();
            };
            script.onerror = (error) => {
		console.error('Failed to load Tone.js.', error);
		reject(error);
            };
            document.head.appendChild(script);
	});
    },
    beforeDestroy() {
	console.log("Destroying...")
        // Stop transport and clean up Tone.js objects
        if (window.Tone && Tone.Transport.state === 'started') {
            Tone.Transport.stop();
            Tone.Transport.cancel();
        }
        if (this.player1) this.player1.dispose();
        if (this.player2) this.player2.dispose();
        if (this.panner1) this.panner1.dispose();
        if (this.panner2) this.panner2.dispose();
        if (this.crossFade) this.crossFade.dispose();
    },
    methods: {
	handleSonifyClick() {
            console.log('Run Sonify Cube...')
            this.sonify_cube(); 
	},
	async loadAudio() {
            try {
		// Wait for Tone.js to load
		await this.toneJsLoadPromise;
		
		// Ensure Tone.js is started
		if (Tone.context.state !== 'running') {
		    await Tone.start();
		    console.log('AudioContext started');
		}
		
		console.log('New audio data incoming...');
		
		// --- Handle one-shot audio with Tone.Player ---
		const onAudioBuffer = await new Tone.Buffer().load(this.on_audio_data_url);
		const oneShotPlayer = new Tone.Player(onAudioBuffer).toDestination();
		oneShotPlayer.volume.value = -0.2; // -0.2dB to not redline anything
		
		// --- Pre-load and pre-route looping cube audio with Tone.js ---
		if (this.cube_audio_data && !this.player1) {
		    console.log('Setting up looping sources with Tone.js...');
		    const cubeAudioBuffer = await new Tone.Buffer().load(this.cube_audio_data_url);
		    // Gotta go fast! (minimise audio latency)
		    Tone.context.lookAhead = 0;
		    
		    // Create two players for the same audio buffer to allow smooth seeking and switching
		    this.player1 = new Tone.Player(cubeAudioBuffer);
		    this.player2 = new Tone.Player(cubeAudioBuffer);
		    
                    // Create panners for stereo separation (debugging)
		    // TODO remove panning layer once happy with implementation
                    this.panner1 = new Tone.Panner(0); // Hard left
                    this.panner2 = new Tone.Panner(0);  // Hard right
		    
		    // Create a gain node for the sonification volume control
		    this.loopGain = new Tone.Gain(0).toDestination();
		    // Create the crossfade and connect it to the gain node
		    this.crossFade = new Tone.CrossFade();
		    this.crossFade.connect(this.loopGain);
		    this.player1.connect(this.panner1);
                    this.panner1.connect(this.crossFade.a);
		    this.player2.connect(this.panner2);
                    this.panner2.connect(this.crossFade.b);
		    
		    // Set initial state: only player1 is audible
		    this.crossFade.fade.value = 0;
		    this.player1.volume.value = 0; // Set target volume
		    this.player2.volume.value = 0;
		    
		    // Calculate and store the precise loop duration.
                    this.loopDuration = this.nsamps / this.sample_rate;
		    
                    this.player1.loopStart = 0 * this.loopDuration; // Custom property to store offset
                    this.player2.loopStart = 0 * this.loopDuration;
		    this.player1.loopEnd = 1 * this.loopDuration; // Custom property to store offset
                    this.player2.loopEnd = 1 * this.loopDuration;
                    this.player1.loop = true;
                    this.player2.loop = true;
		    // Make sure the transport is running for scheduling
		    if (Tone.Transport.state !== 'started') {
			Tone.Transport.start();
		    }
		    // confirm we are ready with audio cue 
		    oneShotPlayer.start();
		    
		    // initialise as not playing
		    this.is_playing = false;
		}
            } catch (error) {
		console.error('Audio load error:', error);
		throw error;
            }
	},
        handleFadeComplete(fadeInitiatedAt) {
            this.isFading = false;
            // If a new lindx value came in while the fade was happening,
            // trigger a new fade to that latest value.
            if (this.lindxLatest !== null && this.lindxLatest !== fadeInitiatedAt) {
                this.handleLindxChange(this.lindxLatest, fadeInitiatedAt);
            } else {
                this.lindxLatest = null;
            }
        },
        handleLindxChange(newVal, oldVal) {
	    // Are we ready to start playback?
            if (!this.player1 || !this.player2 || newVal === oldVal || !window.Tone || !this.is_playing) {
                return;
            }
	    // Is this a sanctioned lindx value?
	    if(newVal > (this.npix-1) || newVal < 0) {
		return;
	    }
	    
            // If a fade is already in progress, queue the latest value and exit.
            if (this.isFading) {
                this.lindxLatest = newVal;
                return;
            }
	    
            this.isFading = true;
            this.lindxLatest = null; // Reset latest since we are processing it now
	    
            const fadeTime = Tone.context.updateInterval; // 30ms crossfade would be ideal, but leads to dropouts
            const loopDuration = this.loopDuration;
            const bufferDuration = this.player1.buffer.duration;
	    
            // Determine which player is inactive and update its loop points.
            const playerToUpdate = this.activePlayer === 1 ? this.player2 : this.player1;
            
            // To combat floating point precision errors when converting from a sample index
            // to a time in seconds.
            const startsamp = (newVal * this.nsamps);
            let newLoopStart = startsamp / this.sample_rate;
	    
            playerToUpdate.loopStart = newLoopStart;
            playerToUpdate.loopEnd = newLoopStart + this.loopDuration;
	    
            // Restart the player at the new offset to apply the new loop points immediately.
            // Calling .start() on a playing source is the correct way to re-trigger it.
            playerToUpdate.start(); //(Tone.now(), newLoopStart);
	    
            // Determine the target for the crossfade (0 for player1, 1 for player2)
            const rampTarget = this.activePlayer === 1 ? 1 : 0;
            // Immediately start the linear ramp on the crossfade
            this.crossFade.fade.linearRampTo(rampTarget, fadeTime, Tone.now());
	    
            // // Switch the active player
            this.activePlayer = this.activePlayer === 1 ? 2 : 1;
	    
	    // Schedule the completion handler using Tone.js's clock for sync
	    Tone.Draw.schedule(() => {
		// This callback is now running in sync with the audio thread		
		this.handleFadeComplete(newVal);
	    }, Tone.now() + fadeTime);
        }
    },
    
    watch: {
	on_audio_data(newVal) {
            if (newVal) {
		this.loadAudio();
            }
	},
	lindx(newVal, oldVal) {
            this.handleLindxChange(newVal, oldVal);
	},
	is_playing(newVal) {
            if (!this.player1 || !this.player2 || !window.Tone || this.is_playing === null) {
                return;
            }
            console.log("is_playing changed to: ", newVal);
            const fadeTime = Tone.context.updateInterval;
            if (newVal) {
                // Start transport if not already running, then start players and fade in
                if (Tone.Transport.state !== 'started') {
                    Tone.Transport.start();
                }
                this.player1.start();
                this.player2.start();
                this.loopGain.gain.rampTo(1, fadeTime);
            } else {
                // Fade out, then schedule players and transport to stop
                this.loopGain.gain.rampTo(0, fadeTime);
                const stopTime = Tone.now() + fadeTime;
                Tone.Transport.schedule((time) => {
                    this.player1.stop(time);
                    this.player2.stop(time);
                }, stopTime);
                Tone.Transport.scheduleOnce((time) => {
                    if (Tone.Transport.state === 'started') {
                        Tone.Transport.stop(time);
                    }
                }, stopTime + 0.01); // Stop transport slightly after players
            }
	}
    },
    computed: {
	on_audio_data_url() {
            return "data:audio/wav;base64," + this.on_audio_data;
	},
	cube_audio_data_url() {
            if (!this.cube_audio_data) {
		return null;
            }
	console.log("loading cube...")
        return "data:audio/wav;base64," + this.cube_audio_data;
      },
      // The string-to-byte conversion is no longer needed with Tone.js's loader
      on_audio_data_str() { return null; },
      cube_audio_data_str() { return null; }
    }
  }
</script>
