import { Select, MenuItem, TextField } from "@mui/material";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import { mutate } from "swr";
import useSWR from "swr";
export default function StepTypePrompt({agent_name, prompt_name}) {
    const [agent, setAgent] = useState(-1);
    const [prompt, setPrompt] = useState(-1);
    const [promptText, setPromptText] = useState("");
    const agents = useSWR('agent', async () => (await axios.get(`${process.env.NEXT_PUBLIC_API_URI ?? 'http://localhost:7437'}/api/agent`)).data.agents);
    const prompts = useSWR('prompt', async () => (await axios.get(`${process.env.NEXT_PUBLIC_API_URI ?? 'http://localhost:7437'}/api/prompt`)).data.prompts);
    useEffect(() => {
        setPromptText(prompt);
    }, [prompt]);
    useEffect(() => {
        setPrompt(prompts.data&&prompt_name?prompts.data.findIndex((prompt) => prompt.name == prompt_name):-1);
    }, [prompts.data, prompt_name]);
    useEffect(() => {
        setAgent(agents.data&&agent_name?agents.data.findIndex((agent) => agent.name == agent_name):-1);
    }, [agents.data, agent_name]);
    return <>
        <Select label="Type" sx={{ mx: "0.5rem" }} value={agent} onChange={(e) => setAgent(e.target.value)}>
            <MenuItem value={-1}>Select an Agent...</MenuItem>
            {agents?.data?.map((agent, index) => {
                return <MenuItem key={index} value={index}>{agent.name}</MenuItem>;
            })}
        </Select>

        <Select label="Prompt" sx={{ mx: "0.5rem" }} value={prompt} onChange={(e) => setPrompt(e.target.value)}>
            <MenuItem value={-1}>Select a Prompt...</MenuItem>
            <MenuItem value={-2}>[New Prompt]</MenuItem>
            {prompts?.data?.map((prompt, index) => {
                return <MenuItem key={index} value={index}>{prompt}</MenuItem>;
            })}
        </Select>

        {prompt===-2?<TextField label="New Prompt" value={promptText} onChange={(e) => setPromptText(e.target.value)} multiline lines={20} sx={{ mx: "0.5rem", flex: 1 }} />:null}
    </>;
}