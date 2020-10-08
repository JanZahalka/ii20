import React from "react";
import ReactDOM from "react-dom";

import Button from "./Button"


class GridControls extends React.Component {
	/*
		Control panel for the grid.
	*/

	constructor(props) {
		super(props);
	}

	render () {
		if (!this.props.ii20Ready) {
			return null;
		}

		let gridControls =
			<div className="gridsettings">
				<div className="gridslider">
					<label htmlFor="nrows" className="gridlabel">Rows:</label>
					<input type="range" id="nrows" name="nrows" min="1" max="10"
					       className="gridsliderelement"
					       value={this.props.nRows}
					       onChange={e => this.props.setSize("rows", e.target.value)} />
				</div>
				<div className="gridslider" style={{marginBottom: "20px"}}>
					<label htmlFor="ncols" className="gridlabel">Columns:</label>
					<input type="range" id="ncols" name="ncols" min="1" max="10"
					       value={this.props.nCols}
					       className="gridsliderelement"
					       onChange={e => this.props.setSize("cols", e.target.value)} />
				</div>
				<div className="gridslider" style={{marginBottom: "20px"}}>
					<div className="tooltipcontainer">
						<span className="tooltip tooltipleftedgealigned">Shows which bucket is being labelled by clicking grid images. Select a bucket by clicking on it below the grid.</span>
						<span className="gridlabel">Labelling:</span>
					</div>
					<span style={{color: this.props.selectedBucketColor, fontWeight: "bold", width: "210px", textAlign: "right"}}>
						{this.props.selectedBucketName}
					</span>
				</div>
				<div className="gridbuttons">
					<Button label="Accept sugg."
					        onClick={this.props.acceptSuggs}
					        tooltip="Labels all images with labels suggested by the model."
					        tooltipLeftEdgeAligned={true}
					        extraStyles={{width: "100px"}}
					        
					 />
					<Button label="Show more"
					        onClick={this.props.interactionRound}
					        tooltip="Sends your feedback (image labels), if any, to the model, updates it, and fetches new relevant images based on the updated model."
					        tooltipRightEdgeAligned={true}
					        extraStyles={{width: "100px"}}
					        
					/>
				</div>
			</div>

		return ReactDOM.createPortal(gridControls, document.getElementById("modecontrols"));
	}
}

export default GridControls;