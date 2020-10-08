# II-20
## About II-20
II-20 is a multimedia analytics system for intelligent analytic categorization of image collections. II-20 loads in your dataset, and allows you to define your categories of relevance - called buckets - to which you add images that you deem relevant. II-20's intelligent AI model learns to understand the buckets, providing you with instant suggestions of relevant items. You can add/delete/redefine/update buckets at any time, making II-20's analytics truly flexible.

There are two modes in which you can conduct your analytics - a classic grid interface, and a playful "Tetris" interface where images flow from the top to the buckets on the bottom (useful if you want to focus on individual images, or just want a change of pace). The process is fully interactive, and the system is responsive even on large data (hundreds of thousands of images to millions).

### Videos:
[Demo video (YouTube)](https://www.youtube.com/watch?v=M2vJQCY_omU)

## Paper
If you are using II-20 or its parts in your scientific work, please cite the II-20 paper:

*J. Zahálka, M. Worring, and Jarke J. van Wijk. **II-20: Intelligent and pragmatic analytic categorization of image collections**. To appear in IEEE Transactions on Visualization and Computer Graphics, February 2021.*

(https://arxiv.org/abs/2005.02149)

## Installation
II-20 is implemented as a Django web app utilizing scientific and deep learning Python libraries in the backend, with the front end being realized through React.js. The software was tested on Ubuntu and Mac OS. I am not aware of any specific reasons it shouldn't run on Windows, but I have not tested that. In this section, we describe how to get started with analytics on demo data.

1. Clone this repository. In further text, `$II20_ROOT` denotes the root directory of the repository. `cd` to it.
