import React from "react";


class Button extends React.Component {
	/*
		A simple style general-purpose button used in the UI.
	*/

	constructor(props) {
		super(props)
	}

	render() {
		let extraClasses = "";
		let tooltip = null;

		if (this.props.label.length > 5) {
			extraClasses = "longtextbutton";
		}

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
				{tooltip}
				<a className={this.props.classOverride ? this.props.classOverride : "button textbutton " + extraClasses}
				   target="_blank" rel="nofollow noopener"
				   onClick={this.props.onClick} style={this.props.extraStyles}>
					{this.props.label}
				</a>
			</div>
		)
	}
	
}

export default Button;