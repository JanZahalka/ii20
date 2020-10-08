import React from "react";

import Button from "./Button"


var FF_IDLE = 0;
var FF_PROCESSING = 1;


class FastForward extends React.Component {
	/*
		The fast-forward view.
	*/

	constructor(props) {
		super(props);

		this.state = {
			ffBucket: {
				name: "<choose>",
				color: "white"
			},
			ffStatus: FF_IDLE
		}
	}

	setFfBucket = (newFfBucket) => {
		/*
			Set the bucket to be fast-forwarded.
		*/
		
		this.setState({
			ffBucket: newFfBucket
		})
	}

	fastForward = () => {
		/*
			Perform the fast-forward, submitting the request to the backend and go to
			the bucket view for FF review.
		*/
		if (this.state.ffBucket["name"] == "<choose>") {
			return;
		}

		let nFf = parseInt(document.getElementById("ffnoimages").value);

		if (isNaN(nFf) || nFf <= 0) {
			alert("The number of fast-forwarded images must be a positive integer!");
			return;
		}

		this.setState({
			ffStatus: FF_PROCESSING
		})

		let requestParams = {
			method: "POST",
			headers: {
				"Accept": "application/json",
            	"Content-Type": "application/json",
				"X-CSRFToken": csrfToken
			},
			body: JSON.stringify({
				"bucket": this.state.ffBucket["id"],
				"n_ff": nFf,
			})
		};

		fetch("/fast_forward", requestParams)
			.then(() => {this.setState({ffStatus: FF_IDLE})})
			.then(() => {this.props.setOutstandingFastForward(this.state.ffBucket["id"])})
			.then(this.props.close)
	}


	render() {
		if (!this.props.visible) {
			return null;
		}

		let closeButtonFunc;
		let ffButtonFunc;
		let ffButtonLabel;

		if (this.state.ffStatus == FF_IDLE) {
			closeButtonFunc = this.props.close;
			ffButtonFunc = this.fastForward;
			ffButtonLabel = "Fast-forward"
		}
		else if (this.state.ffStatus == FF_PROCESSING) {
			ffButtonFunc = null;			
			ffButtonLabel = "Processing..."
		}

		return (
			<div className="overlay">
					<div className="overlaycontent" style={{width: "auto", height: "auto"}}>
						<div className="overlayheader">
							<h1>&#9654;&#9654; Fast-forward</h1>
							<Button label="&times;" onClick={closeButtonFunc}/>
						</div>
						<div className="ffcontent">
							<div className="ffentry">
								<span className="fflabel">Fast-forwarding bucket:</span>
								<div className="bvorderingwrapper bvcontrolitem" style={{marginLeft: "25px"}}>
									<button className="bvorderingdropdown" style={{color: this.state.ffBucket["color"]}}>{this.state.ffBucket["name"]}</button>
									<div className="bvorderingdropcontent">
									{
										this.props.bucketOrdering.map((b, i) => {
											return (<div key={"transfer" + i} className="bvorderingoption"
											             style={{color: this.props.buckets[b]["color"]}}
											             onClick={() => this.setFfBucket(this.props.buckets[b])}>
											             {this.props.buckets[b]["name"]}
											        </div>
											       )
										})
									}
									</div>
								</div>
							</div>
							<div className="ffentry">
								<label htmlFor="ffnoimages" className="fflabel">Number of images:&nbsp;&nbsp;</label>
								<input type="text" id="ffnoimages" name="ffnoimages" />
							</div>
							<div className="ffentry">
								<Button label={ffButtonLabel}
								        onClick={ffButtonFunc}
								        extraStyles={{marginTop: "50px"}}/>
							</div>
						</div>
					</div>
			</div>
		)
	}
}

export default FastForward;