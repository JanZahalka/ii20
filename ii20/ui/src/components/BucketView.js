import React from "react";

import Button from "./Button"

let SORT_BY_LABELS = {
	confidence: "Bucket conf.",
	fast_forward: "Fast-forward",
	newest_first: "Newest first",
	oldest_first: "Oldest first"
}

class BucketView extends React.Component {
	/*
		The bucket view that shows bucket contents (images) and provides the option to
		transfer images between buckets.
	*/


	constructor(props) {
		super(props);

		this.state = {
			viewMode: "bvgriditem",
			ordering: "Bucket confidence",
			transferBucket: this.props.bucketOrdering[0] == this.props.bucketKey ? this.props.buckets[this.props.bucketOrdering[1]] : this.props.buckets[this.props.bucketOrdering[0]],
			transferMode: "move",
			selected: new Set()
		}
	}

	componentDidUpdate = (prevProps) => {
		if (prevProps.buckets != this.props.buckets) {
			this.setState({
				transferBucket: this.props.bucketOrdering[0] == this.props.bucketKey ? this.props.buckets[this.props.bucketOrdering[1]] : this.props.buckets[this.props.bucketOrdering[0]]
			})
		}
	}


	toggleViewMode = () => {
		/*
			Switches between the display modes: 1 image in a row (column mode) and 3
			images in a row (grid mode).
		*/
		
		let newViewMode;

		if (this.state.viewMode == "bvgriditem") {
			newViewMode = "bvcolitem";
		}
		else {
			newViewMode = "bvgriditem";
		}

		this.setState({
			viewMode: newViewMode
		})
	}

	selectImage = (image) => {
		/*
			Selects/deselects an image in the bucket view.
		*/

		let selected = this.state.selected;

		if (selected.has(image)) {
			selected.delete(image);
		}
		else {
			selected.add(image);
		}

		this.setState({
			selected: selected
		})
	}


	setTransferBucket = (newTransferBucket) => {
		/*
			Sets the destination bucket for an upcoming transfer. If the discard pile is
			selected, it overrides the transfer mode and sets it to "move" (images cannot
			be copied to discard pile from buckets - that would mean the image is both
			relevant and not relevant, confusing the model).
		*/
		this.setState({
			transferBucket: newTransferBucket,
			transferMode: this.state.transferMode == "copy" && newTransferBucket["id"] == 0 ? "move" : this.state.transferMode,
		})
	}

	setTransferMode = (newTransferMode) => {
		/*
			Sets the transfer mode: copy or move.
		*/
		this.setState({
			transferMode: newTransferMode
		})
	}

	clearSelection = () => {
		/*
			Clears (deselects) the selected images.
		*/
		this.setState({
			selected: new Set()
		})
	}

	close = () => {
		/*
			Closes the bucket view.
		*/
		
		this.clearSelection();
		this.props.close();
	}

	transferImages = () => {
		/*
			Transfers images between buckets (actually done one level above, in
			BucketControlPanel, this clears the selection beforehand).
		*/
		let selected = this.state.selected

		this.clearSelection();

		this.props.transferImages(selected,
			                      this.props.bucket["id"],
			                      this.state.transferBucket["id"],
			                      this.state.transferMode)
	}


	render() {
		if (!this.props.visible) {
			return null;
		}

		let bvViewColBgImg;
		let bvViewGridBgImg;

		if (this.state.viewMode == "bvgriditem") {
			bvViewColBgImg = "url('/static/ui/bv_colview.svg')";
			bvViewGridBgImg = "url('/static/ui/bv_gridview_selected.png')";
		}
		else {
			bvViewColBgImg = "url('/static/ui/bv_colview_selected.png')";
			bvViewGridBgImg = "url('/static/ui/bv_gridview.svg')";	
		}

		return(
			<div className="overlay" id={this.props.id}>
					<div className="overlaycontent">
						<div className="overlayheader">
							<h1 style={{color: this.props.bucket["color"], fontSize: "250%"}}>{this.props.bucket["name"]}</h1>

							<Button label="&times;" onClick={this.close}/>
						</div>

						<div className="bucketviewcontrols">
							<div className="bvviewtoggles">
								<span className="bvcontrolitem">View:</span>
								<div className="bvviewtoggleicon bvcontrolitem"
								     style={{backgroundImage: bvViewColBgImg}}
								     onClick={this.toggleViewMode} />
								<div className="bvviewtoggleicon bvcontrolitem"
								     style={{backgroundImage: bvViewGridBgImg}}
								     onClick={this.toggleViewMode} />
							</div>

							<div className="bvorderingouter">
								<span className="bvcontrolitem">Sort by:</span>
								<div className="bvorderingwrapper">
									<button className="bvorderingdropdown">{SORT_BY_LABELS[this.props.sortBy]}</button>
									<div className="bvorderingdropcontent">
										<div className="bvorderingoption" onClick={() => this.props.refreshBucketViewData("confidence")}>Bucket confidence</div>
										<div className="bvorderingoption" onClick={() => this.props.refreshBucketViewData("newest_first")}>Newest in bucket first</div>
										<div className="bvorderingoption" onClick={() => this.props.refreshBucketViewData("oldest_first")}>Oldest in bucket first</div>
									</div>
								</div>
							</div>

							<div className="bvtransfercontrols">
								<div className="bvtransfersettings">
									<div className="bvtransferdest">
										<span className="bvcontrolitem">Transfer to:</span>
										<div className="bvorderingwrapper bvcontrolitem">
											<button className="bvorderingdropdown" style={{color: this.state.transferBucket["color"]}}>{this.state.transferBucket["name"]}</button>
											<div className="bvorderingdropcontent">
											{
												this.props.bucketOrdering.map((b, i) => {
													if (b == this.props.bucketKey) {
														return null;
													}

													return (<div key={"transfer" + i} className="bvorderingoption"
													             style={{color: this.props.buckets[b]["color"]}}
													             onClick={() => this.setTransferBucket(this.props.buckets[b])}>
													             {this.props.buckets[b]["name"]}
													        </div>
													       )
												})
											}
											</div>
										</div>
									</div>
									<div className="bvtransfermode">
										<label htmlFor="move" className="bvcontrolitem" style={{textAlign: "right"}}>Move</label>
										<input className="bvcontrolitem" type="radio" id="move" name="transfermode" value="move"
											   checked={this.state.transferMode == "move" ? true : false}
										       onChange={() => this.setTransferMode("move")} />
										<input className="bvcontrolitem"
										       type="radio" id="copy" name="transfermode" value="copy"
										       disabled={(this.props.bucket["id"] == 0 || this.state.transferBucket["id"] == 0) ? true : false}
										       checked={this.state.transferMode == "copy" ? true : false}
										       onChange={() => this.setTransferMode("copy")} />
										<label htmlFor="copy" className="togglelabel" className="bvcontrolitem">Copy</label>
									</div>
									</div>
								<div className="bvtransferbutton">
									<Button label="Transfer"
										    onClick={this.transferImages}
									        extraStyles={{marginBottom: "20px", width: "100px"}} />
								</div>
								
							</div>
							
						</div>

						<div className="bvgrid">
							{
								this.props.bucketViewData.map((imgEntry, i) => {
									let ffIcon = null;

									if (imgEntry["is_fast_forward"]) {
										ffIcon = <img src="/static/ui/fast_forward.svg"
										              className="imgdecorator"
										          />;
									}

									return (					


										<div className={this.state.viewMode} key={"bvgriddiv" + i}
											 style={{
											 	borderColor: this.state.selected.has(imgEntry["image"]) ? "white" : imgEntry["confidence_color"],
											    backgroundImage: "url('" + imgEntry["url"] + "')"
											 }}
											 onClick={() => this.selectImage(imgEntry["image"])}

										>
											{ffIcon}
											
										</div>
									)
								})
							}
						</div>
						
					</div>
				</div>
		)
	}
}

export default BucketView;