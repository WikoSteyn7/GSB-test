import DOMPurify from 'dompurify';
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import { ChatResponse } from "../../api";

const CharacterStreamer = ({ finalAnswer, eventSource, nonEventString, onStreamingComplete, classNames, typingSpeed = 30 }: 
  { finalAnswer?: (data: string) => void; eventSource?: any; nonEventString?: string, onStreamingComplete: any; classNames?: string; typingSpeed?: number }) => {
  const [output, setOutput] = useState('');
  const queueRef = useRef<string[]>([]); // Now TypeScript knows this is an array of strings
  const processingRef = useRef(false);
  const [answer, setAnswer] = useState<ChatResponse>();
  const isEndEventTriggered = useRef(false);

  const finalAnswerIfReady = () => {
    if (!processingRef.current && finalAnswer) { // Check if processing is indeed done
        finalAnswer(output); // Now safe to call finalAnswer
    }
    // If processing is not done, finalAnswer will be called after processing finishes
};

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

    const handleStartup = async (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        setAnswer(data);
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
            // Optionally call finalAnswer here if it should happen at every character update
            if (finalAnswer && queueRef.current.length === 0 && isEndEventTriggered.current) {
                finalAnswer(updatedOutput);
            }
            return updatedOutput;
        });
      } else {
        clearInterval(intervalId);
        processingRef.current = false;
      }
    }, typingSpeed); // Adjust based on desired "typing" speed
  };

  return <div className={classNames}><ReactMarkdown children={output} rehypePlugins={[rehypeRaw, rehypeSanitize]}></ReactMarkdown></div>;
};

export default CharacterStreamer;
