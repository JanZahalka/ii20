import React from "react";

import BucketControlPanel from "./BucketControlPanel";
import Button from "./Button";
import FastForward from "./FastForward";


class SidePanel extends React.Component {
	
	constructor(props) {
		super(props);

		this.state = {
			ffVisible: false
		}
	}

	ffOpen = () => {
		this.setState({
			ffVisible: true
		})
	}

	ffClose = () => {
		this.setState({
			ffVisible: false
		})
	}


	render() {
		let recordInsight = null;

		if (this.state.recordInsightVisible) {
			recordInsight =
				<div className="overlay">
					<div className="overlaycontent" style={{width: "auto", height: "auto"}}>
						<div className="overlayheader">
							<h1>Record your insight:</h1>
							<Button label="&times;" onClick={this.recordInsightClose}/>
						</div>
						<textarea className="insightinput" id="insight" />
						<Button label="Submit insight"
						        onClick={this.submitInsight}
						 />
					</div>
				</div>
		}

		return (<div id="sidepanel">
					<BucketControlPanel buckets={this.props.buckets} bucketOrdering={this.props.bucketOrdering}
										visibleBucketView={this.props.visibleBucketView}
										hasOutstandingFastForward={this.props.hasOutstandingFastForward}
					                    refreshBuckets={this.props.refreshBuckets}
					                    checkResponseError={this.props.checkResponseError}
					                    setPostTransferReloadFlag={this.props.setPostTransferReloadFlag}
					                    setVisibleBucketView={this.props.setVisibleBucketView}
					                    resolveFastForward={this.props.resolveFastForward}
					 />
					 <div className="divider" />					 
					<div id="modecontrols">
						<div className="toggle" style={{marginBottom: "20px"}}>
							<div className="toggleoption">
								<div className="tooltipcontainer">
									<label htmlFor="tetris" className="togglelabel" style={{textAlign: "right"}}>Tetris</label>
								</div>
								<input type="radio" id="tetris" name="mode" value="tetris"
								       checked={this.props.mode === "tetris"}
								       onChange={this.props.toggleMode}
								       style={{marginLeft: "10px", marginRight: "50px"}} />
							</div>
							<div className="toggleoption">
								<input type="radio" id="grid" name="mode" value="grid"
								       checked={this.props.mode === "grid"}
								       onChange={this.props.toggleMode}
								       style={{marginRight: "10px"}} />
								<div className="tooltipcontainer">
									<label htmlFor="grid" className="togglelabel">Grid</label>
								</div>
							</div>
							
						</div>
						
					</div>
					<div className="divider" />
					<div id="miscbuttons">
						<Button label="&#9654;&#9654; Fast-forward"
							    onClick={this.ffOpen}
						        extraStyles={{marginBottom: "20px"}}
						        tooltip="Quickly add images to a bucket based on its current model."
						/>
						<br/>

						<FastForward visible={this.state.ffVisible}
						             close={this.ffClose}
						             buckets={this.props.buckets}
						             bucketOrdering={this.props.bucketOrdering}
						             setOutstandingFastForward={this.props.setOutstandingFastForward}
						 />						
					</div>
				</div>
		)
	}
}

export default SidePanel;