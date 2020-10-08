import React from "react";

import Button from "./Button"
import GridControls from "./GridControls"


let timer;
let doubleClickLock;

class Grid extends React.Component {
	/*
		The grid image view.
	*/

	constructor(props) {
		super(props);

		this.state = {
			imageData: [],
			nCols: 7,
			nRows: 4,
			labels: {},

			imagePreviewActive: false,
			imagePreviewUrl: null,
			imagePreviewFilename: null,
			imagePreviewBucket: null
		}
	}

	componentDidMount() {
		this.interactionRound();
	}

	componentDidUpdate(prevProps, prevState) {
		if (prevProps.nBucketsActiveAndTrained != this.props.nBucketsActiveAndTrained
			|| (!prevProps.postTransferReloadNeeded && this.props.postTransferReloadNeeded)) {
			this.interactionRound();
		}
	}

	interactionRound = () => {
		/*
			Performs an interaction round, submitting user feedback to the backend and
			obtaining new recommendations.
		*/

		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify(this.state.labels)
		};

		fetch("/interaction_round", requestParams)
			.then(this.props.checkResponseError)
			.then(response => response.json())
			.then(newGridData => {
				this.setState({
					imageData: newGridData["grid_images"],
					labels: newGridData["feedback"]
				})
			})
			.then(this.props.refreshBuckets)
			.then(() => this.props.setPostTransferReloadFlag(false))
			.catch(error => alert(error));
	}

	labelImage = (imageId, bucket) => {
		/*
			Label an image with the bucket label (or deselect it if already
			labelled)
		*/
		if (bucket == null) {
			return;
		}

		let updatedLabels = this.state.labels;

		if (updatedLabels[imageId] == bucket) {
			updatedLabels[imageId] = null;
		}
		else {
			updatedLabels[imageId] = bucket;
		}

		this.setState({
			labels: updatedLabels
		})
	}

	openImagePreview = (imageUrl, imageFilename, bucket) => {
		/*
			Previews the magnified image in an overlay.
		*/
		this.setState({
			imagePreviewActive: true,
			imagePreviewUrl: imageUrl,
			imagePreviewFilename: imageFilename,
			imagePreviewBucket: bucket
		})
	}

	closeImagePreview = () => {
		/*
			Closes the preview.
		*/
		this.setState({
			imagePreviewActive: false,
			imagePreviewUrl: null,
			imagePreviewBucket: null
		})
	}

	gridImageClick = (imageId, bucket) => {
		/*
			A hacky (yay Javascript) function to discern between a single and a double
			click on an image. This is a single click.
		*/

		let me = this;

		timer = setTimeout(function() {
	      if (!doubleClickLock) {
	        me.labelImage(imageId, bucket);
	      }
	      doubleClickLock = false;
	    }, 100);
	}

	gridImageDoubleClick = (imageId, imageFilename) => {
		/*
			A hacky (yay Javascript) function to discern between a single and a double
			click on an image. This is a double click.
		*/
		clearTimeout(timer);
		doubleClickLock = true;
		this.openImagePreview(imageId, imageFilename);
	}

	setSize = (dim, newSize) => {
		/*
			Resizes the grid to new dimensions.
		*/
		if ((dim == "rows" && this.state.nRows == newSize) ||
			(dim == "cols" && this.state.nCols == newSize)) {
			return;
		}

		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify({
				"dim": dim,
				"new_size": newSize
			})
		};

		fetch("/grid_set_size", requestParams)
			.then(this.props.checkResponseError)
			.then(response => response.json())
			.then(newGridData => {
				if (dim == "rows") {
					this.setState({
						imageData: newGridData["grid_images"],
						labels: newGridData["feedback"],
						nRows: newSize
					})
				}
				else {
					this.setState({
						imageData: newGridData["grid_images"],
						labels: newGridData["feedback"],
						nCols: newSize
					})
				}
				console.log(newGridData["feedback"]);
			})
			.catch(error => alert(error));
	}

	deselectInvisibleImages = () => {
		/*
			A helper function that deselects images that are now invisible (they were
			part of a larger-sized grid which was downscaled).
		*/
		for (let i = this.state.nCols * this.state.nRows; i<100; i++) {
			this.state.labels[this.state.imageData[i]["image"]] = null;
		}
	}

	acceptSuggs = () => {
		/*
			Labels all suggestions for all buckets as relevant for their respective
			bucket (essentially, accepting suggestions as they came from the model).
		*/
		let updatedLabels = this.state.labels;

		for (let i = 0; i<this.state.imageData.length; i++) {
			let imgEntry = this.state.imageData[i];

			if (imgEntry["bucket"] > 0) {
				updatedLabels[imgEntry["image"]] = imgEntry["bucket"];
			}
		}
	}

	render() {
		let imagePreview = null;

		if (this.state.imagePreviewActive) {
			imagePreview =
				<div className="overlay" id={this.props.id}>
					<div className="overlaycontent">
						<div className="overlayheader">
							<h1>{this.state.imagePreviewFilename}</h1>
							<Button label="&times;" onClick={this.closeImagePreview}/>
						</div>
						<div className="imagepreview"
						     style={{
						     	backgroundImage: "url('" + this.state.imagePreviewUrl + "')",
						     	borderColor: this.state.imagePreviewBucket == null ? "#181818" : this.props.buckets[this.state.imagePreviewBucket]["color"]
						     }}
						     onClick={this.closeImagePreview}
						     onContextMenu={(e) => {
						     	e.preventDefault();
						     	this.closeImagePreview();
						     }}/>
					</div>
				</div>
		}


		return (<div className="grid">
					{
						this.state.imageData.map((imgEntry, i) => {
							let border;
							let bucketLabel = this.state.labels[imgEntry["image"]];

							if (bucketLabel != null) {
								border = "6px solid " + this.props.buckets[bucketLabel]["color"];
							}
							else if (imgEntry["bucket"] > 0) {
								border = "6px dashed " + imgEntry["confidence_color"];
							}
							else {
								border = "6px solid #181818"
							}

							let alIcon = null;

							if (imgEntry["is_al_query"]) {
								alIcon = <img src="/static/ui/active_learning.svg"
								              className="imgdecorator"
										  />;
							}

							return (<div className="gridimg" key={i}
										 style={{
										 	backgroundImage: "url('" + imgEntry["url"] + "')",
										 	width: (Math.floor(0.99*this.props.workspaceWidth/this.state.nCols) - 22) + "px",
										 	height: (Math.floor(0.99*this.props.workspaceHeight/this.state.nRows) - 22)+ "px",
										 	border: border
										 }}
										 onClick={() => {this.labelImage(imgEntry["image"], this.props.selectedBucket)}}
										 onContextMenu={(e) => {
										 					e.preventDefault();
										 					this.openImagePreview(imgEntry["url"], imgEntry["filename"], bucketLabel);
										 				}}
								    >
								    	{alIcon}
								    </div>
						    )
						})	
					}
					<GridControls ii20Ready={this.props.ii20Ready}
					              nRows={this.state.nRows}
					              nCols={this.state.nCols}
					              setSize={this.setSize}
					              selectedBucketName={this.props.buckets[this.props.selectedBucket]["name"]}
					              selectedBucketColor={this.props.buckets[this.props.selectedBucket]["color"]}
					              interactionRound={this.interactionRound}
					              acceptSuggs={this.acceptSuggs}
					 />
					 {imagePreview}
				</div>)
	}
}

export default Grid;