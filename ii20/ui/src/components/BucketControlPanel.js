import React from "react";

import Button from "./Button"
import BucketControlItem from "./BucketControlItem";
import BucketView from "./BucketView";


class BucketControlPanel extends React.Component {
	/*
		The bucket control panel. Many functions actually correspond to child components
		(mostly BucketView), as the state is maintained here for the control panel and
		bucket view to be synchronized

	*/


	constructor(props) {
		super(props);

		this.state = {
			bucketViewData: [],
			bucketViewDataSortBy: "confidence",
			fastForwardLoaded: false,
			viewToggle: false
		}
	}

	componentDidUpdate = (prevProps, prevState) => {
		if (this.props.hasOutstandingFastForward) {
			this.refreshBucketViewData("fast_forward");
		}
	}

	fireBucketUpdate = (endpointUrl, requestBody) => {
		/*
			An umbrella method for changing the bucket (create/rename/delete...), firing
			a POST update to the backend.
		*/

		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify(requestBody)
		};

		fetch(endpointUrl, requestParams)
			.then(this.props.checkResponseError)
			.then(this.props.refreshBuckets)
			.catch(error => alert(error));
	}

	createBucket = () => {
		/*
			Creates a new bucket.
		*/
		
		this.fireBucketUpdate("/create_bucket", {});
	}


	deleteBucket = (bucketId) => {
		/*
			Deletes a bucket (prompts the user first).
		*/
		
		let userConfirmed = confirm("This will irreversibly delete the bucket along with all its contents. Do you wish to proceed?")

		if (!userConfirmed) {
			return;
		}

		let requestBody = {
			"bucket_id": bucketId
		}

		this.fireBucketUpdate("/delete_bucket", requestBody)
	}

	renameBucket = (bucketId, oldBucketName) => {
		/*
			Renames a bucket.
		*/
		let newBucketName = prompt("Bucket name:", oldBucketName);

		if (newBucketName.length >= 16) {
			newBucketName = newBucketName.substring(0, 16)
			alert("Bucket names must be max 16 characters long. Your bucket name was truncated to '" + newBucketName + "'.")
		}

		let requestBody = {
			"bucket_id": bucketId,
			"new_bucket_name": newBucketName
		}

		this.fireBucketUpdate("/rename_bucket", requestBody);
	}

	swapBuckets = (bucket1Id, bucket2Id) => {
		/*
			Swaps the position of two buckets.
		*/

		let requestBody = {
			"bucket1_id": bucket1Id,
			"bucket2_id": bucket2Id
		}

		this.fireBucketUpdate("/swap_buckets", requestBody);
	}

	toggleBucket = (bucketId) => {
		/*
			Activates/deactivates a bucket.
		*/
		let requestBody = {
			"bucket_id": bucketId
		}

		this.fireBucketUpdate("/toggle_bucket", requestBody);
	}

	openBucketView = (bucketId) => {
		/*
			Opens the bucket view for the given bucket.
		*/
		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify({
				"bucket_id": bucketId,
				"sort_by": this.state.bucketViewDataSortBy
			})
		};

		fetch("/bucket_view_data", requestParams)
			.then(this.props.checkResponseError)
			.then(response => response.json())
			.then(bucketViewData => {
				this.setState({
					bucketViewData: bucketViewData,
				})
			})
			.then(() => this.props.setVisibleBucketView(bucketId))
			.catch(error => alert(error));
	}

	refreshBucketViewData = (sortBy) => {
		/*
			Refreshes the data for the bucket view, so that it shows up-to-date bucket
			contents.
		*/
		if (sortBy != "fast_forward" && sortBy == this.state.bucketViewDataSortBy) {
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
				"bucket_id": this.props.visibleBucketView,
				"sort_by": sortBy
			})
		};
		
		fetch("/bucket_view_data", requestParams)
			.then(this.props.checkResponseError)
			.then(response => response.json())
			.then(bucketViewData => {
				this.setState({
					bucketViewData: bucketViewData,
					bucketViewDataSortBy: sortBy,
					fastForwardLoaded: sortBy == "fast_forward"
				})
			})
			.then(this.props.resolveFastForward)
			.catch(error => alert(error));
	}


	transferImages = (images, bucketSrc, bucketDst, mode) => {
		/*
			Transfers images between buckets.
		*/
		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify({
				"images": Array.from(images),
				"bucket_src": bucketSrc,
				"bucket_dst": bucketDst,
				"mode": mode,
				"sort_by": this.state.bucketViewDataSortBy
			})
		};

		fetch("/transfer_images", requestParams)
			.then(this.props.checkResponseError)
			.then(response => response.json())
			.then(bucketViewData => {
				this.setState({
					bucketViewData: bucketViewData
				})
			})
			.then(this.props.refreshBuckets)
			.then(() => this.props.setPostTransferReloadFlag(true))
			.catch(error => alert(error));
	}

	closeBucketView = (bucketId) => {
		/*
			Closes the bucket view (deciding whether to commit a fast-forward or not).
		*/
		if (this.state.fastForwardLoaded) {
			this.commitFastForwardAndClose(bucketId);
		}
		else {
			this.props.setVisibleBucketView(-1);
		}
	}

	commitFastForwardAndClose = (bucketId) => {
		/*
			Commits fast-forward and closes the bucket view.
		*/
		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify({
				"bucket": bucketId,
			})
		};

		fetch("/ff_commit", requestParams)
			.then(this.props.checkResponseError)
			.then(() => {
				this.setState({
					fastForwardLoaded: false
				})
			})
			.then(() => this.props.setVisibleBucketView(-1))
			.catch(error => alert(error));
	}

	render() {
		return (
			<div id="bucketcontrol">
				<div className="bucketitems">
					{
						this.props.bucketOrdering.map((b, i) => {
							let bucketName = this.props.buckets[b]["name"];
							let bucketUp = (i == 0) ? null : this.props.bucketOrdering[i - 1];
							let bucketDown = (i == this.props.bucketOrdering.length - 2) ? null : this.props.bucketOrdering[i + 1];

							let swapUpFunc;
							let swapDownFunc;

							if (bucketUp === null) {
								swapUpFunc = null;
							}
							else {
								swapUpFunc = () => {this.swapBuckets(b, bucketUp)};
							}

							if (bucketDown === null) {
								swapDownFunc = null;
							}
							else {
								swapDownFunc = () => {this.swapBuckets(b, bucketDown)};
							}

							let isDiscard = (b == 0) ? true : false;
							let toggleBucketFunc;

							if (isDiscard) {
								toggleBucketFunc = null;
							}
							else {
								toggleBucketFunc = () => {this.toggleBucket(b)};
							}


							return (
								<div className="bucketcontrolitemouter" key={"outer" + i}>
								<BucketView key={"view" + i} bucketKey={b}
								            bucket={this.props.buckets[b]}
								            visible={this.props.visibleBucketView == b ? true : false}
								            bucketViewData={this.state.bucketViewData}
								            sortBy={this.state.bucketViewDataSortBy}								            
								            refreshBucketViewData={this.refreshBucketViewData}
								            transferImages={this.transferImages}
								            setPostTransferReloadFlag={this.props.setPostTransferReloadFlag}
								            close={() => {this.closeBucketView(b)}}

								            buckets={this.props.buckets}
								            bucketOrdering={this.props.bucketOrdering}
								/>
								<BucketControlItem key={i} name={bucketName}
								                   color={this.props.buckets[b]["color"]}
								                   isDiscard={isDiscard}
								                   viewBucket={() => {this.openBucketView(b)}}
								                   deleteBucket={() => {this.deleteBucket(b)}}
								                   renameBucket={() => {this.renameBucket(b, bucketName)}}
								                   swapUp={swapUpFunc}
								                   swapDown={swapDownFunc}
								                   isActive={this.props.buckets[b]["active"]}
								                   toggleBucket={toggleBucketFunc}
								               	   tooltipBelow={i == 0}
								/>
								</div>
							)
						})						
					}
				</div>
				<Button label="Create bucket"
				        onClick={this.createBucket}
				/>
			</div>
		)
	}

}

export default BucketControlPanel;