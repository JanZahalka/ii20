import React from "react";

import TetrisControls from "./TetrisControls"


var TETRIS_N_STEPS = 5;

var TETRIS_PAUSED = 0;
var TETRIS_DESCENDING = 1;
var TETRIS_PROCESSING = 2;
var TETRIS_IMG_LOADED = 3;
var TETRIS_BUCKETS_REFRESHED = 4;

var TETRIS_PAUSE_BETWEEN_IMAGES = 100;

var Y_BOTTOM_IMG_HIDDEN = 25000;


const sleep = (milliseconds) => {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}


class TetrisTile extends React.Component {
	/*
		The tile for the Tetris view (essentially, THE Tetris image view, as the rest
		of the workspace is an empty space).
	*/


	constructor(props) {
		super(props);

		this.state = {
			y: Y_BOTTOM_IMG_HIDDEN,
			yStepsDescended: 0,

			speed: 500,

			imageUrl: null,
			imageFilename: null,
			imageId: null,

			descendLock: false,

			bucketId: 0, /* Discard */
			confidenceColor: "lime", /* Something bright... this should never draw */
			suggLineThickness: 10,
			isALQuery: false,

			status: TETRIS_PROCESSING,
			prevStatus: null,
			autoPlay: false,

			metadataOverlayOn: false,
			pausedBeforeMeta: null
		}
	}

	componentDidMount() {
		document.addEventListener("keydown", this.tetrisControls, false);
		document.addEventListener("keyup", this.metadataOverlayOff, false);
		this.interactionRound(true);
	}

	shouldComponentUpdate(nextProps, nextState) {
		if (this.state.status == TETRIS_PAUSED &&
			nextState.status != TETRIS_PAUSED) {
			return true;
		}

		if (nextState.descendLock) {
			return false;
		}

		if (nextState.status === TETRIS_BUCKETS_REFRESHED) {
			return true;
		}

		if (nextState.bucketId === this.state.bucketId &&
			nextState.y === this.state.y &&
			nextState.imageUrl === this.state.imageUrl &&
			nextState.autoPlay === this.state.autoPlay &&
			nextProps.width == this.props.width &&
			nextState.descendLock === this.state.descendLock &&
			nextState.metadataOverlayOn == this.state.metadataOverlayOn) {
			return false;
		}

		return true;
	}

	componentDidUpdate() {
		if (this.state.status == TETRIS_DESCENDING) {
			this.descend();
		}
		else if (this.state.status == TETRIS_PROCESSING) {
			this.interactionRound(false);
		}
	}

	componentWillUnmount() {
		document.removeEventListener("keydown", this.tetrisControls, false);
		document.removeEventListener("keyup", this.metadataOverlayOff, false);
	}

	bucketActivityCheck = () => {
		/*
			Check whether the bucket the image is hovering over is active
			(the user can deactivate it asynchronously).
			If it is not, the image will appear over the discard pile.
		*/

		if (!this.props.buckets[this.state.bucketId]["active"]) {
			this.setState({
				bucketId: 0,
				autoPlay: false
			})

		}
	}

	descend = () => {
		/*
			Descend the tile.
		*/

		this.bucketActivityCheck();

		if (this.state.descendLock || this.state.status != TETRIS_DESCENDING) {
			return;
		}

		this.setState({
			descendLock: true
		});

		sleep(this.state.speed)
		.then(() => {
			if (this.state.yStepsDescended <= TETRIS_N_STEPS) {
				this.setState({
					y: this.state.yStepsDescended * this.props.height/TETRIS_N_STEPS,
					yStepsDescended: this.state.yStepsDescended + 1	
				})
			}
			else {
				this.setState({
					y: Y_BOTTOM_IMG_HIDDEN,
					status: TETRIS_PROCESSING
				})
			}
		})
		.then(() => {
			this.setState({
				descendLock: false
			})
		});		
	}

	interactionRound = (sendEmptyFeedback) => {
		/*
			When the tile reaches bottom, perform an interaction round, obtaining a new
			suggestion to load at the top.
		*/

		let userFeedback;

		if (sendEmptyFeedback) {
			userFeedback = {};
		}
		else {
			userFeedback = {
				[this.state.imageId]: this.state.bucketId
			}
		}

		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify(userFeedback)
		};

		fetch("/interaction_round", requestParams)
			.then(this.props.checkResponseError)
			.then(response => response.json())
			.then(nextImageData => {
				this.setState({
					imageUrl: nextImageData["url"],
					imageFilename: nextImageData["filename"],
					imageId: nextImageData["image"],
					bucketId: nextImageData["bucket"],
					autoPlay: nextImageData["bucket"] == 0 ? false : true,
					confidenceColor: nextImageData["confidence_color"],
					suggLineThickness: nextImageData["sugg_line_thickness"],
					isALQuery: nextImageData["is_al_query"],
					status: TETRIS_IMG_LOADED
				})
			})
			.then(this.props.refreshBuckets)
			.then(() => sleep(TETRIS_PAUSE_BETWEEN_IMAGES))
			.then(() => {
				this.setState({
					status: TETRIS_DESCENDING,
					y: 0,
					yStepsDescended: 0
				})
			})
			.catch(error => alert(error));
	}

	setPaused = (isBeingPaused) => {
		/*
			Pause/unpause Tetris.
		*/

		if (isBeingPaused) {
			this.setState({
				prevStatus: this.state.status,
				status: TETRIS_PAUSED
			});
		}
		else {
			this.setState({
				status: this.state.prevStatus
			})
		}
	}

	incrementSpeed = (isIncreasing) => {
		/*
			Increase/decrease descent speed.
		*/

		if ((isIncreasing && this.state.speed <= 10)
			|| (!isIncreasing && this.state.speed >= 2000)) {
			return
		}

		if (isIncreasing) {
			if (this.state.speed > 10) {
				this.setState({speed: this.state.speed / 1.5});
			}
		}
		else {
			if (this.state.speed < 2000) {
				this.setState({speed: this.state.speed * 1.5});
			}
		}
	}

	tetrisControls = (event) => {
		/*
			Handles keyboard hotkeys for Tetris.
		*/
		if (this.props.tetrisControlsSuppressed) {
			return;
		}

		if (event.key === "ArrowLeft") {
			let bucketIdx = this.props.buckets[this.state.bucketId]["banner_ordering"];

			if (bucketIdx > 0) {
				this.setState({
					bucketId: this.props.bannerOrdering[bucketIdx - 1],
					autoPlay: false
				});
			}
		}
		if (event.key === "ArrowRight") {
			let bucketIdx = this.props.buckets[this.state.bucketId]["banner_ordering"];

			if (bucketIdx < this.props.bannerOrdering.length - 1) {
				this.setState({
					bucketId: this.props.bannerOrdering[bucketIdx + 1],
					autoPlay: false
				});
			}
		}
		if (event.key === "ArrowDown") {
			event.preventDefault();
			this.incrementSpeed(true);
		}
		if (event.key === "ArrowUp") {
			event.preventDefault();
			this.incrementSpeed(false);
		}
		if (event.key === " ") {
			this.setPaused(this.state.status != TETRIS_PAUSED)
		}
		if (event.key === "i") {
			this.setState({
				metadataOverlayOn: true,				
			})

			/* Used due to the keydown firing repeatedly */
			if (this.state.pausedBeforeMeta == null) {
				this.setState({
					pausedBeforeMeta: this.state.status == TETRIS_PAUSED
				})

				if (!this.state.pausedBeforeMeta) {
					this.setPaused(true)
				}
			}
		}
	}

	metadataOverlayOff = (event) => {
		/*
			Switches off the metadata overlay.
		*/
		if (event.key == "i") {
			this.setState({
				metadataOverlayOn: false
			})

			if (!this.state.pausedBeforeMeta) {
				this.setPaused(false);	
			}

			this.setState({
				pausedBeforeMeta: null
			});
		}

	}

	render() {
		let suggBorder = null;
		let suggLine = null;
		let alIcon = null;
		let metadataOverlay = null;

		let x = this.props.buckets[this.state.bucketId]["banner_ordering"]*this.props.width;

		if (this.state.isALQuery) {
			alIcon = <image x={x + 0.45*this.props.width}
			                y={this.state.y + 25}
			                width={0.05*this.props.width}
			                height={0.1*this.props.height}
			                href="/static/ui/active_learning.svg"
					  />;
		}

		if (this.props.buckets[this.state.bucketId]["active"] && this.state.autoPlay) {
			suggLine = <line x1={x + 0.5*this.props.width}
							 x2={x + 0.5*this.props.width}
							 y1={this.state.y + 0.5*this.props.height}
							 y2={this.props.yBottom}
							 style={{
								stroke: this.state.confidenceColor,
								strokeWidth: this.state.suggLineThickness
							}}
					    />;
		}

		if (this.state.metadataOverlayOn) {
			metadataOverlay =
				<g>
					<rect width={this.props.xRight} height={this.props.yBottom}
					      fill="black" opacity="0.4" />
					<text x={this.props.xRight/2} y="75" textAnchor="middle"
					      fill="white" stroke="black" strokeWidth="2px"
					      fontFamily="sans-serif" fontSize="32px" fontWeight="bolder">
						{this.state.imageFilename}
					</text>
				</g>;
		}

		return(<svg id="workspacesvg">
				{suggLine}
				{suggBorder}				
				<image x={x}
			          y={this.state.y}
			          width={this.props.width}
			          height={this.props.height}
			          href={this.state.imageUrl}    
			   	/>
			   	{alIcon}
			   	<TetrisControls ii20Ready={this.props.ii20Ready}
			   	                isPaused={this.state.status == TETRIS_PAUSED}
			   	                setPaused={this.setPaused}
			   	                incrementSpeed={this.incrementSpeed}
			   	/>
			   	{metadataOverlay}
			   </svg>)
	}
}

export default TetrisTile;