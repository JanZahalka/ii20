import React from "react";

class IconButton extends React.Component {
	/*
		A general icon button (used chiefly in the bucket control panel).
	*/

	constructor(props) {
		super(props)
	}

	render() {
		let tooltip = null;

		if (this.props.tooltip) {
			let tooltipStyle = "tooltip";

			if (this.props.tooltipBelow) {
				tooltipStyle += " tooltipbelow";
			}

			if (this.props.tooltipRightEdgeAligned) {
				tooltipStyle += " tooltiprightedgealigned"
			}
	
			tooltip = <span className={tooltipStyle}>{this.props.tooltip}</span>;
		}

		return (
			<div className="buttoncontainer tooltipcontainer" align="center">
				<a className="button" target="_blank" rel="nofollow noopener"
				   onClick={this.props.onClick}>
					{tooltip}
					<div className={"iconbutton " + this.props.iconButtonClass} style={this.props.extraStyles} />
				</a>
			</div>
		)
	}
	
}

export default IconButton;