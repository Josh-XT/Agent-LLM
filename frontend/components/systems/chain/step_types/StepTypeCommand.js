import { Select, MenuItem, TextField } from "@mui/material";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import { mutate } from "swr";
import useSWR from "swr";
export default function StepTypeCommand({agent_name, prompt_name}) {
    const [command, setCommand] = useState(-1);
    // TODO: Get commands directly from API without going through agent.
    const agents = useSWR('agent', async () => (await axios.get(`${process.env.NEXT_PUBLIC_API_URI ?? 'http://localhost:7437'}/api/agent`)).data.agents);
    const commands = useSWR('command', async () => (await axios.get(`${process.env.NEXT_PUBLIC_API_URI ?? 'http://localhost:7437'}/api/agent/${agents[0].agent_name}/command`)).data.agents);
    return <>
        <Select label="Command" sx={{ mx: "0.5rem" }} value={prompt} onChange={(e) => setCommand(e.target.value)}>
            <MenuItem value={-1}>Select a Command...</MenuItem>
            {commands?.data?.map((command, index) => {
                return <MenuItem key={index} value={index}>{command}</MenuItem>;
            })}
        </Select>

        {prompt===-2?<TextField label="New Prompt" multiline lines={20} sx={{ mx: "0.5rem", flex: 1 }} />:null}
    </>;
}