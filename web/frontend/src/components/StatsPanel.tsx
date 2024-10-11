import { Typography } from "@mui/material";

export default function StatsPanel({currentTick}: {currentTick: number}) {
    return <Typography m ={2}>tick: {currentTick}</Typography>
}
