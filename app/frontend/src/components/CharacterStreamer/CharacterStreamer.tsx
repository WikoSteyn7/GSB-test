import DOMPurify from 'dompurify';
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import { Approaches, ChatResponse } from "../../api";

const CharacterStreamer = ({ finalAnswer, eventSource, nonEventString, onStreamingComplete, classNames, approach = Approaches.ChatWebRetrieveRead, typingSpeed = 30 }: 
  { finalAnswer?: (data: ChatResponse) => void; approach?: Approaches, eventSource?: any; nonEventString?: string, onStreamingComplete: any; classNames?: string; typingSpeed?: number }) => {
  const [output, setOutput] = useState('');
  const queueRef = useRef<string[]>([]); // Now TypeScript knows this is an array of strings
  const processingRef = useRef(false);
  const [answer, setAnswer] = useState<ChatResponse>();
  const [startUpData, setStartUpData] = useState({ data_points: [], web_citation_lookup: {}, work_citation_lookup: {}, thought_chain: {} });
  const isEndEventTriggered = useRef(false);


  const checkAndFinalizeAnswer = () => {
    //console.log('Checking final conditions', {
    //  processing: processingRef.current,
   //   queueLength: queueRef.current.length,
    //  endTriggered: isEndEventTriggered.current,
      // dataPoints: startUpData.data_points.length
    //});
    // Ensure all data is ready: processing finished, end event triggered, and startUpData loaded
    if (queueRef.current.length === 0 && isEndEventTriggered.current && (Object.keys(startUpData.web_citation_lookup).length > 0 || Object.keys(startUpData.work_citation_lookup).length > 0)) {
        if (finalAnswer) {
            finalAnswer({
                answer: output,
                thoughts: "",
                data_points: startUpData.data_points,
                approach: approach,
                web_citation_lookup: startUpData.web_citation_lookup,
                work_citation_lookup: startUpData.work_citation_lookup,
                thought_chain: startUpData.thought_chain
            });
            console.log('Final answer sent with startup data:', startUpData);
        }
    }
  };

  useEffect(() => {
    // checkAndFinalizeAnswer();
    console.log(startUpData);
    // checkAndFinalizeAnswer();
  }, [startUpData]);

  useEffect(() => {
    checkAndFinalizeAnswer();
  }, [output]);

  useEffect(() => {
    if (!eventSource && nonEventString) {
        console.log("Event source not found");
        queueRef.current = queueRef.current.concat(nonEventString.split(''));
        if (!processingRef.current) {
            processQueue();
        }
    }
    const handleMessage = async (event: MessageEvent) => {
        // Process the Markdown content to HTML immediately
        //const processedHTML = await marked(event.data);
        // Split the processed HTML into an array of characters and add it to the queue
        // We use markdown, <br> does nothing for us. We need to replace it with \n
        const processedHTML = event.data.replace(/<br>/g, '\n');
        queueRef.current = queueRef.current.concat(processedHTML.split(''));
        // queueRef.current = queueRef.current.concat("\n\n");
        if (!processingRef.current) {
            processQueue();
        }
    };

    const handleStartup = (event: MessageEvent) => {
        const startup = JSON.parse(event.data);
        console.log(event.data);
        setStartUpData({
            data_points: startup.data_points,
            web_citation_lookup: startup.web_citation_lookup,
            work_citation_lookup: startup.work_citation_lookup,
            thought_chain: startup.thought_chain
        });
        
    };

    const handleEnd = () => {
      isEndEventTriggered.current = true;
      if (onStreamingComplete) {
        onStreamingComplete(); // Call any additional cleanup or processes needed
      }
    };

    if (eventSource) {
      eventSource.addEventListener('startup', handleStartup);
      eventSource.addEventListener('message', handleMessage);
      eventSource.addEventListener('end', handleEnd);
    }

    return () => {
      if (eventSource) {
        eventSource.removeEventListener('startup', handleStartup);
        eventSource.removeEventListener('message', handleMessage);
        eventSource.removeEventListener('end', handleEnd);
      }
    };
  }, [eventSource, nonEventString]);

  const processQueue = () => {
    processingRef.current = true;
    const intervalId = setInterval(() => {
      if (queueRef.current.length > 0) {
        const char = queueRef.current.shift();
        setOutput((prevOutput) => {
            const updatedOutput = prevOutput + char;
            return updatedOutput;
        });
      } else {
        processingRef.current = false;
        checkAndFinalizeAnswer();
        clearInterval(intervalId);
      }
    }, typingSpeed); // Adjust based on desired "typing" speed
  };

  return <div className={classNames}><ReactMarkdown children={output} rehypePlugins={[rehypeRaw, rehypeSanitize]}></ReactMarkdown></div>;
};

export default CharacterStreamer;
