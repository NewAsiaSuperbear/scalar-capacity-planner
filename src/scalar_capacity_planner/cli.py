import argparse
from dataclasses import asdict
import json
from . import ModelSpec,CapacityPlanner


def main():
    parser=argparse.ArgumentParser(description="Synthetic assumed AI capacity example; no AI trace calibration or deployment.")
    parser.add_argument("--k",type=float,default=3)
    parser.add_argument("--Y",type=float,default=2)
    parser.add_argument("--grid-size",type=int,default=401)
    parser.add_argument("--gap-tolerance",type=float,default=.05)
    args=parser.parse_args()
    spec=ModelSpec(a=(2,-.5),b=(3,-.5),d=(8,2),p=1,h=4,mean_band=(-.1,.1),mad_center=0,mad_upper=.5,nmax=4)
    planner=CapacityPlanner(spec,args.grid_size)
    result=planner.solve(args.k,args.Y,gap_tolerance=args.gap_tolerance)
    print(json.dumps({"data_label":"SYNTHETIC ASSUMPTIONS; NO AI TRACES", "model":asdict(spec),"k":args.k,"Y":args.Y,"is_dpp":planner.is_dpp,"result":asdict(result)},indent=2,allow_nan=False))

if __name__=="__main__": main()
