import React from "react";

import IconButton from "./IconButton"

var BG_COLOR_INACTIVE = "#242424";
var BG_COLOR_ACTIVE = "#181818";
var FG_COLOR_INACTIVE = "#808080";

class BucketControlItem extends React.Component {
	/*
		One row entry in the bucket control panel.
	*/

	constructor(props) {
		super(props);

		let bgColor;
		let fgColor;

		if (props.isActive) {
			fgColor = props.color;
			bgColor = BG_COLOR_ACTIVE;
		}
		else {
			fgColor = FG_COLOR_INACTIVE;
			bgColor = BG_COLOR_INACTIVE;
		}

		this.state = {
			color: fgColor,
			backgroundColor: bgColor
		}
	}

	render() {
		let bgColor;
		let fgColor;

		if (this.props.isActive) {
			fgColor = this.props.color;
			bgColor = BG_COLOR_ACTIVE;
		}
		else {
			fgColor = FG_COLOR_INACTIVE;
			bgColor = BG_COLOR_INACTIVE;
		}

		let bucketIcon;
		let bucketControls;
		let arrows;

		if (this.props.isDiscard) {
			bucketIcon = <img src="/static/ui/discard.svg" className="bucketicon" />;
			bucketControls = <div className="bucketcontrols">
								 <IconButton iconButtonClass="viewiconbutton"
								             onClick={this.props.viewBucket}
								             tooltip="Opens the bucket view where you can review and manipulate its images."
								             tooltipBelow={this.props.tooltipBelow}
								             extraStyles={{backgroundColor: bgColor}}/>
							 </div>;
			arrows = <div className="arrows" />;
		}
		else {
			bucketIcon =
				<svg className="bucketicon" viewBox="0 0 512 550" onClick={this.props.toggleBucket}>
					<g>
					<path d="M445.63,151.704h-28.746C411.956,67.225,341.692,0,256,0S100.044,67.225,95.116,151.704H66.37
							c-5.236,0-9.481,4.245-9.481,9.482v47.407c0,5.236,4.245,9.482,9.481,9.482H86.74l46.121,285.954
							c0.741,4.595,4.708,7.972,9.361,7.972h227.556c4.653,0,8.62-3.377,9.361-7.972l46.121-285.954h20.369
							c5.236,0,9.481-4.245,9.481-9.482v-47.407C455.111,155.949,450.866,151.704,445.63,151.704z M256,18.963
							c75.232,0,136.971,58.728,141.871,132.741H114.129C119.029,77.691,180.768,18.963,256,18.963z M361.704,493.037H150.296
							l-44.347-274.963h300.102L361.704,493.037z M436.148,199.111h-18.963H94.815H75.852v-28.444h360.296V199.111z"
						  style={{fill: fgColor}} />
					</g>
				</svg>;
			bucketControls =
				<div className="bucketcontrols">
					<IconButton iconButtonClass="viewiconbutton"
					            onClick={this.props.viewBucket}
					            tooltip="Opens the bucket view where you can review and manipulate its images."
					            tooltipBelow={this.props.tooltipBelow}
					            extraStyles={{backgroundColor: bgColor}}/>
					<IconButton iconButtonClass="editiconbutton"
					            onClick={this.props.renameBucket}
					            tooltip="Renames the bucket (16 character limit)."
					            tooltipBelow={this.props.tooltipBelow}
					            tooltipRightEdgeAligned={true}
					            extraStyles={{backgroundColor: bgColor}} />
					<IconButton iconButtonClass="deleteiconbutton"
					            onClick={this.props.deleteBucket}
					            tooltip="Deletes the bucket along with its trained model."
					            tooltipBelow={this.props.tooltipBelow}
					            tooltipRightEdgeAligned={true}
					            extraStyles={{backgroundColor: bgColor}} />
				</div>;
			arrows =
				<div className="arrows">
					<IconButton iconButtonClass="uparrowiconbutton"
					            onClick={this.props.swapUp}
					            tooltip="Swaps this bucket's position with the bucket one position up."
					            tooltipBelow={this.props.tooltipBelow}
					            tooltipRightEdgeAligned={true}
					            extraStyles={{backgroundColor: bgColor}} />
					<IconButton iconButtonClass="downarrowiconbutton"
					            onClick={this.props.swapDown}
					            tooltip="Swaps this bucket's position with the bucket one position down."
					            tooltipBelow={this.props.tooltipBelow}
					            tooltipRightEdgeAligned={true}
					            extraStyles={{backgroundColor: bgColor}} />
				</div>;

		}


		return (
			<div className="bucketcontrolitem" style={{backgroundColor: bgColor}}>
				{bucketIcon}
				<span className="bucketlabel" onClick={this.props.toggleBucket} style={{color: fgColor}}>{this.props.name}</span>
				
				{bucketControls}

				{arrows}
				
			</div>
		)
	}
}

export default BucketControlItem;