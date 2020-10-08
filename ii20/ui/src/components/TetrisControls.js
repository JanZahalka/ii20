import React from "react";
import ReactDOM from "react-dom";

import Button from "./Button"


class TetrisControls extends React.Component {
	/*
		The controls for the Tetris image view.
	*/

	constructor(props) {
		super(props);
	}

	render() {
		if (!this.props.ii20Ready) {
			return null;
		}

		let tetrisControls = 
				<div className="modesettings">
					<div className="pauseplay">
						<Button label={this.props.isPaused ? "\u25B6" : "||"}
						        onClick={() => this.props.setPaused(!this.props.isPaused)}
						        tooltip="Play/pause the Tetris flow."
						 />
					</div>
					<div className="speedcontrols">
						<Button label="+"
						        onClick={() => this.props.incrementSpeed(true)}
						        tooltip="Increase the descent speed of the images."/>
						<span>&nbsp;&nbsp;&nbsp;Speed&nbsp;&nbsp;&nbsp;</span>
						<Button label="-"
						        onClick={() => this.props.incrementSpeed(false)}
						        tooltip="Decrease the descent speed of the images." />
					</div>
				</div>

		return ReactDOM.createPortal(tetrisControls, document.getElementById("modecontrols"));
	}
}

export default TetrisControls;