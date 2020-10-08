import React from "react";
import ReactDOM from "react-dom";

import BucketBox from "./BucketBox"
import Button from "./Button"
import Grid from "./Grid"
import SidePanel from "./SidePanel"
import TetrisTile from "./TetrisTile"


class II20Main extends React.Component {
	/*
		The main, parent class of the II-20 UI. Maintains a lot of state for descendant
		components (those parts that need synchronization around the UI).
	*/

	constructor(props) {
		super(props);

		this.state = {
			workspaceWidth: document.getElementById("uicontainer").clientWidth * 0.75,
			workspaceHeight: document.getElementById("uicontainer").clientHeight * 0.8,
			mode: "grid",
			buckets: initBuckets,
			bucketOrdering: initBucketOrdering,
			bannerOrdering: initBucketOrdering,
			nBucketsActiveAndTrained: 0,
			ii20Ready: false,
			postTransferReloadNeeded: false,

			selectedBucket: 0,
			
			visibleBucketView: -1,
			hasOutstandingFastForward: false,

			tetrisControlsSuppressed: false,

			strategy: "focus"
		};
	}

	componentDidMount() {
		window.addEventListener("resize", this.handleWindowResize);
	}

	componentWillUnmount() {
		window.removeEventListener("resize", this.handleWindowResize);
	}


	refreshBuckets = () => {
		/*
			Refreshes bucket information: which buckets exist, which are active, what
			the archetypes are, their order...
		*/
		fetch("/bucket_info")
			.then(this.checkResponseError)
			.then(response => response.json())
			.then(responseData => {
				this.setState({
					buckets: responseData["buckets"],
					bucketOrdering: responseData["bucket_ordering"],
					bannerOrdering: responseData["banner_ordering"],
					selectedBucket: responseData["buckets"][this.state.selectedBucket]["active"] ? this.state.selectedBucket : 0,
					nBucketsActiveAndTrained: responseData["n_active_and_trained"]
				});

			})
			.catch(error => alert(error));
	}

	checkResponseError = (response) => {
		/*
			A helper function for raising errors encountered during request handling.
		*/

		if (!response.ok) {
			throw Error(response.statusText);
		}

		return response;
	}

	handleWindowResize = () => {
		/*
			Scales the UI properly when the browser window is resized.
		*/

		this.setState({
			workspaceWidth: document.getElementById("uicontainer").clientWidth * 0.75,
			workspaceHeight: document.getElementById("uicontainer").clientHeight * 0.8
		});
	}

	toggleMode = () => {
		/*
			Toggles between grid and Tetris.
		*/

		fetch("/toggle_mode")
			.then(this.checkResponseError)
			.then(response => response.json())
			.then(imageData => {
				document.activeElement.blur();

				let newMode;

				if (this.state.mode == "tetris") {
					newMode = "grid";
				}
				else {
					newMode = "tetris";
				}

				this.setState({
					mode: newMode,
				})
			})
			.catch(error => alert(error));
	}

	ready = () => {
		/*
			A helper function setting the UI to ready for the user. This flag is
			used to handle various pre-loadings across the system.
		*/
		this.setState({
			ii20Ready: true
		})
	}

	changeSelectedBucket = (b) => {
		/*
			Selects a different bucket (for labelling images in the grid).
		*/
		this.setState({
			selectedBucket: b
		})
	}

	setPostTransferReloadFlag = (newFlagValue) => {
		/*
			Flags the buckets as requiring update after image transfer.
		*/

		this.setState({
			postTransferReloadNeeded: newFlagValue
		})
	}

	setVisibleBucketView = (newVisibleBucketView) => {
		/*
			Opens up a bucket view for the given bucket.
		*/
		this.setState({
			visibleBucketView: newVisibleBucketView
		})

		this.refreshBuckets();
	}

	setOutstandingFastForward = (newOutstandingFastForwardBucket) => {
		/*
			Sets the bucket with an outstanding (uncommitted) fast-forward.
		*/
		this.setState({
			visibleBucketView: newOutstandingFastForwardBucket,
			hasOutstandingFastForward: true
		})
	}

	resolveFastForward = () => {
		/*
			Resolves a commited fast forward.
		*/
		this.setState({
			hasOutstandingFastForward: false
		})	
	}

	setSuppressTetrisControls = (suppressFlag) => {
		/*
			Suppresses Tetris controls (required for when an overlay such as a bucket
			view is active, otherwise Tetris hotkeys would trigger Tetris in the background.)
		*/
		this.setState({
			tetrisControlsSuppressed: suppressFlag
		})
	}
	
	render() {
		let nActiveBuckets = 0;
		let keys = Object.keys(this.state.buckets);
		for (let i = 0; i<keys.length; i++) {
			if (this.state.buckets[keys[i]]["active"]) {
				nActiveBuckets++;
			}
		}

		let bucketWidth = (100/nActiveBuckets) + "%";
		let bucketY = this.state.workspaceHeight*0.8


		let workspaceContent;

		if (this.state.mode == "tetris") {
			let tetrisTileWidth = this.state.workspaceWidth/nActiveBuckets;

			workspaceContent =
				<TetrisTile width={tetrisTileWidth}
							height={this.state.workspaceHeight / 2}
							xRight={this.state.workspaceWidth}
							yBottom={this.state.workspaceHeight}
							buckets={this.state.buckets}
							bucketOrdering={this.state.bucketOrdering}
							bannerOrdering={this.state.bannerOrdering}
							tetrisControlsSuppressed={this.state.tetrisControlsSuppressed}

							checkResponseError={this.checkResponseError}
							refreshBuckets={this.refreshBuckets}
							ii20Ready={this.state.ii20Ready}
						
				/>
		}
		else {
			workspaceContent =
				<Grid ii20Ready={this.state.ii20Ready}
					  selectedBucket={this.state.selectedBucket}
					  buckets={this.state.buckets}
					  bannerOrdering={this.state.bannerOrdering}
					  nBucketsActiveAndTrained={this.state.nBucketsActiveAndTrained}

					  workspaceWidth={this.state.workspaceWidth}
					  workspaceHeight={this.state.workspaceHeight}

					  checkResponseError={this.checkResponseError}
					  refreshBuckets={this.refreshBuckets}
					  postTransferReloadNeeded={this.state.postTransferReloadNeeded}
					  setPostTransferReloadFlag={this.setPostTransferReloadFlag}
				/>
		}

		return (
			<div id="ii20interface">
				<SidePanel mode={this.state.mode}
				           buckets={this.state.buckets}
				           bucketOrdering={this.state.bucketOrdering}
				           strategy={this.state.strategy}
				           refreshBuckets={this.refreshBuckets}
				           checkResponseError={this.checkResponseError}
				           toggleMode={this.toggleMode}
				           visibleBucketView={this.state.visibleBucketView}
				           hasOutstandingFastForward={this.state.hasOutstandingFastForward}
				           setPostTransferReloadFlag={this.setPostTransferReloadFlag}
				           setVisibleBucketView={this.setVisibleBucketView}
				           setOutstandingFastForward={this.setOutstandingFastForward}
				           resolveFastForward={this.resolveFastForward}
				           setSuppressTetrisControls={this.setSuppressTetrisControls}
			     />
				<div id="workspace">
					{workspaceContent}
					<div id="bucketbanner">
						{
							this.state.bannerOrdering.map((b, i) => {
								return (
									<BucketBox key={i} i={i} bucketWidth={bucketWidth}
									           y={bucketY}
									           bucket={this.state.buckets[b]}
									           changeSelectedBucket={() => {this.changeSelectedBucket(b)}}
									/>
								);
							})
						}
					</div>
				</div>
			</div>
		)
	}
}

const II20Wrapper = document.getElementById("uicontainer");

if (II20Wrapper) {
	let ii20 = ReactDOM.render(<II20Main />, II20Wrapper);
	ii20.ready();
}