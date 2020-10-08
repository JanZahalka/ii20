import React from "react";


class BucketBox extends React.Component {
	/*
		The bucket box in the bucket banner (on the bottom of the image view).
	*/

	constructor(props) {
		super(props)
	}

	render() {
		let transform = "translate(" + this.props.i*this.props.bucketWidth + "," + this.props.y + ")";
		
		return (
			<div className="bucketbox" style={{width: this.props.bucketWidth, backgroundColor: this.props.bucket["color"]}}
			     onClick={this.props.changeSelectedBucket}>
				<div className="bucketboxheader">
					<span className="bucketboxname">{this.props.bucket["name"]} </span>
					<span className="bucketboximgcount">&nbsp;({this.props.bucket["n_images"]})</span>
				</div>
				<div className="archetypecontainer">
					{
						this.props.bucket["archetypes"].map((archetypeUrl, i) => {
							return (
								<img key={"archetype" + i}
								     src={archetypeUrl}
								     className="archetype" />
							)
						})
					}
				</div>
			</div>
		)
		
	}
}

export default BucketBox;